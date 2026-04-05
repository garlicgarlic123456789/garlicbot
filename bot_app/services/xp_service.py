from dataclasses import dataclass
from typing import Mapping
import random

from bot_app.repositories.xp_repository import xp_repository
from bot_app.types.readability_contracts import XpSetting


@dataclass
class AttendanceRewardResult:
    status: str
    streak: int = 0
    check_xp: int = 0
    boost_check_xp: int = 0
    streak_bonus: int = 0
    total_xp: int = 0
    unit: str = ""


def _coerce_xp_setting(setting: XpSetting | list | tuple | None) -> XpSetting:
    if isinstance(setting, XpSetting):
        return setting
    if not setting:
        return XpSetting(False, None, None, None, None, "")
    return XpSetting(
        enabled=bool(setting[0]),
        chat_xp=setting[1],
        chat_xp_cooldown=setting[2],
        voice_xp=setting[3],
        voice_xp_cooldown=setting[4],
        unit=setting[5] or "",
    )


def _resolve_xp_setting(server_id: int, xp_settings: Mapping[int, object], repository) -> XpSetting:
    if server_id in xp_settings:
        return _coerce_xp_setting(xp_settings[server_id])
    return _coerce_xp_setting(repository.get_xp_setting(server_id))


def apply_message_xp(
    *,
    server_id: int,
    user_id: int,
    xp_settings: Mapping[int, object],
    last_exp_time: dict[int, dict[int, float]],
    now_monotonic: float,
    repository=xp_repository,
):
    if server_id not in xp_settings:
        return False

    setting = _coerce_xp_setting(xp_settings[server_id])
    if not setting.enabled:
        return False

    gain_xp = setting.chat_xp
    cooldown = setting.chat_xp_cooldown
    if gain_xp is None or cooldown is None:
        return False

    if cooldown == 0:
        repository.add_xp(server_id, user_id, gain_xp)
        repository.add_month_xp(server_id, user_id, gain_xp)
        return True

    if server_id not in last_exp_time:
        last_exp_time[server_id] = {}

    if user_id in last_exp_time[server_id]:
        if now_monotonic - last_exp_time[server_id][user_id] < cooldown:
            return False

    last_exp_time[server_id][user_id] = now_monotonic
    repository.add_xp(server_id, user_id, gain_xp)
    repository.add_month_xp(server_id, user_id, gain_xp)
    return True


async def process_attendance_reward(
    *,
    server_id: int,
    user_id: int,
    user_role_ids,
    xp_settings: Mapping[int, object],
    using_server: int,
    server_booster_role_id: int,
    repository=xp_repository,
    rng=random,
):
    setting = _resolve_xp_setting(server_id, xp_settings, repository)
    if setting.enabled is False:
        return AttendanceRewardResult(status="xp_disabled")

    settings = await repository.get_attendance_settings(server_id)
    if settings["on_off"] is False:
        return AttendanceRewardResult(status="attendance_disabled")

    attendance_check, streak = repository.process_attendance(server_id, user_id)
    if not attendance_check:
        return AttendanceRewardResult(status="already_checked", streak=streak)

    streak_bonus = 0
    if server_id == using_server:
        if streak > 1:
            streak_bonus = rng.randrange(50, 101, 10)
        if streak >= 7:
            streak_bonus += rng.randrange(50, 151, 10)
        if streak >= 14:
            streak_bonus += rng.randrange(100, 201, 10)
        if streak >= 30:
            streak_bonus += rng.randrange(300, 501, 10)

    check_xp = rng.randrange(settings["minimum"], settings["maximum"] + 1, settings["step"])

    if server_id == using_server and server_booster_role_id in user_role_ids:
        boost_check_xp = rng.randrange(300, 1001, 10)
    else:
        boost_check_xp = 0

    total_xp = check_xp + boost_check_xp + streak_bonus
    repository.add_xp(server_id, user_id, total_xp)
    repository.add_month_xp(server_id, user_id, total_xp)

    unit = setting.unit
    return AttendanceRewardResult(
        status="success",
        streak=streak,
        check_xp=check_xp,
        boost_check_xp=boost_check_xp,
        streak_bonus=streak_bonus,
        total_xp=total_xp,
        unit=unit,
    )
