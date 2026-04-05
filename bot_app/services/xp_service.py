from typing import Mapping
import random

from commands.return_level import return_level
from bot_app.repositories.xp_repository import xp_repository
from bot_app.types.readability_contracts import (
    AttendanceRewardResult,
    MessageXpApplyResult,
    XpAdjustmentResult,
    XpRankingEntry,
    XpRankingPage,
    XpSetting,
    XpSnapshot,
    XpTransferResult,
)


def _coerce_xp_setting(setting: XpSetting | list | tuple | None) -> XpSetting:
    if isinstance(setting, XpSetting):
        return setting
    if not setting:
        return XpSetting(False, None, None, None, None, "")
    enabled, chat_xp, chat_xp_cooldown, voice_xp, voice_xp_cooldown, unit = setting
    return XpSetting(
        enabled=bool(enabled),
        chat_xp=chat_xp,
        chat_xp_cooldown=chat_xp_cooldown,
        voice_xp=voice_xp,
        voice_xp_cooldown=voice_xp_cooldown,
        unit=unit or "",
    )


def _resolve_xp_setting(server_id: int, xp_settings: Mapping[int, object], repository) -> XpSetting:
    if server_id in xp_settings:
        return _coerce_xp_setting(xp_settings[server_id])
    return _coerce_xp_setting(repository.get_xp_setting(server_id))


def get_effective_xp_setting(
    *,
    server_id: int,
    xp_settings: Mapping[int, object],
    repository=xp_repository,
) -> XpSetting:
    """Return the named XP setting contract for a server."""
    return _resolve_xp_setting(server_id, xp_settings, repository)


def apply_message_xp(
    *,
    server_id: int,
    user_id: int,
    xp_settings: Mapping[int, object],
    last_exp_time: dict[int, dict[int, float]],
    now_monotonic: float,
    repository=xp_repository,
) -> MessageXpApplyResult:
    if server_id not in xp_settings:
        return MessageXpApplyResult(status="skipped_missing_setting")

    setting = _coerce_xp_setting(xp_settings[server_id])
    if not setting.enabled:
        return MessageXpApplyResult(status="skipped_disabled")

    gain_xp = setting.chat_xp
    cooldown = setting.chat_xp_cooldown
    if gain_xp is None or cooldown is None:
        return MessageXpApplyResult(status="skipped_missing_value")

    if cooldown == 0:
        repository.add_xp(server_id, user_id, gain_xp)
        repository.add_month_xp(server_id, user_id, gain_xp)
        return MessageXpApplyResult(status="awarded", awarded_xp=gain_xp)

    if server_id not in last_exp_time:
        last_exp_time[server_id] = {}

    if user_id in last_exp_time[server_id]:
        if now_monotonic - last_exp_time[server_id][user_id] < cooldown:
            return MessageXpApplyResult(status="skipped_cooldown")

    last_exp_time[server_id][user_id] = now_monotonic
    repository.add_xp(server_id, user_id, gain_xp)
    repository.add_month_xp(server_id, user_id, gain_xp)
    return MessageXpApplyResult(status="awarded", awarded_xp=gain_xp)


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
) -> AttendanceRewardResult:
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


def get_xp_snapshot(
    *,
    server_id: int,
    user_id: int,
    xp_settings: Mapping[int, object],
    using_server: int,
    repository=xp_repository,
    leveler=return_level,
) -> XpSnapshot:
    setting = _resolve_xp_setting(server_id, xp_settings, repository)
    total_xp = repository.get_xp(server_id, user_id)
    month_xp = repository.get_month_xp(server_id, user_id)
    old_xp = repository.get_old_xp(server_id, user_id) if server_id == using_server else None
    return XpSnapshot(
        total_xp=total_xp,
        month_xp=month_xp,
        total_level=leveler(total_xp),
        month_level=leveler(month_xp),
        unit=setting.unit,
        old_xp=old_xp,
    )


def transfer_xp(
    *,
    server_id: int,
    sender_user_id: int,
    receiver_user_id: int,
    amount: int,
    xp_settings: Mapping[int, object],
    repository=xp_repository,
) -> XpTransferResult:
    setting = _resolve_xp_setting(server_id, xp_settings, repository)
    if repository.get_xp(server_id, sender_user_id) < amount:
        return XpTransferResult(status="insufficient_balance", amount=amount, unit=setting.unit)

    repository.add_xp(server_id, sender_user_id, -amount)
    repository.add_month_xp(server_id, sender_user_id, -amount)
    repository.add_xp(server_id, receiver_user_id, amount)
    repository.add_month_xp(server_id, receiver_user_id, amount)
    return XpTransferResult(status="success", amount=amount, unit=setting.unit)


def adjust_xp(
    *,
    server_id: int,
    user_id: int,
    amount: int,
    xp_settings: Mapping[int, object],
    repository=xp_repository,
) -> XpAdjustmentResult:
    setting = _resolve_xp_setting(server_id, xp_settings, repository)
    repository.add_xp(server_id, user_id, amount)
    repository.add_month_xp(server_id, user_id, amount)
    return XpAdjustmentResult(
        amount=amount,
        total_xp=repository.get_xp(server_id, user_id),
        month_xp=repository.get_month_xp(server_id, user_id),
        unit=setting.unit,
    )


def get_xp_ranking_page(
    *,
    server_id: int,
    scope: str,
    page: int,
    page_size: int,
    xp_settings: Mapping[int, object],
    repository=xp_repository,
    leveler=return_level,
) -> XpRankingPage:
    setting = _resolve_xp_setting(server_id, xp_settings, repository)
    if scope == "month":
        ranking_title = "경험치 순위 (월간)"
        exp_data = repository.get_all_month_xp(server_id)
    else:
        ranking_title = "경험치 순위"
        exp_data = repository.get_all_xp(server_id)

    sorted_exp = sorted(exp_data.items(), key=lambda item: item[1], reverse=True)
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    rankings = sorted_exp[start_index:end_index]
    entries = tuple(
        XpRankingEntry(
            user_id=int(user_id),
            xp=xp_amount,
            level=leveler(xp_amount),
            rank=index,
        )
        for index, (user_id, xp_amount) in enumerate(rankings, start=start_index + 1)
    )
    return XpRankingPage(
        title=ranking_title,
        page=page,
        total_pages=len(sorted_exp) // page_size + 1,
        unit=setting.unit,
        entries=entries,
    )
