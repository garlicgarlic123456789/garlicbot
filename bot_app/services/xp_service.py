from dataclasses import dataclass
import random

from bot_app.repositories.xp_repository import xp_repository


@dataclass
class AttendanceRewardResult:
    status: str
    streak: int = 0
    check_xp: int = 0
    boost_check_xp: int = 0
    streak_bonus: int = 0
    total_xp: int = 0
    unit: str = ""


def apply_message_xp(
    *,
    server_id: int,
    user_id: int,
    xp_settings,
    last_exp_time,
    now_monotonic: float,
    repository=xp_repository,
):
    if server_id not in xp_settings:
        return False

    setting = xp_settings[server_id]
    if not setting[0]:
        return False

    gain_xp = setting[1]
    cooldown = setting[2]

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
    xp_settings,
    using_server: int,
    server_booster_role_id: int,
    repository=xp_repository,
    rng=random,
):
    setting = repository.get_xp_setting(server_id)
    if server_id not in xp_settings:
        xp_settings[server_id] = setting

    if server_id not in xp_settings or xp_settings[server_id][0] is False:
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

    unit = xp_settings[server_id][5]
    return AttendanceRewardResult(
        status="success",
        streak=streak,
        check_xp=check_xp,
        boost_check_xp=boost_check_xp,
        streak_bonus=streak_bonus,
        total_xp=total_xp,
        unit=unit,
    )
