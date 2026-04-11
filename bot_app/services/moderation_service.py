from dataclasses import dataclass

from bot_app.repositories.moderation_repository import moderation_repository
from bot_app.types.readability_contracts import WarnLimitSettingResult, WarningStatusSnapshot


DEFAULT_REASON = "*(사유 입력되지 않음)*"


@dataclass
class WarningActionResult:
    old_count: int
    delta: int
    new_count: int
    warn_max: int | None
    reason: str
    reached_limit: bool


@dataclass
class TimeoutActionResult:
    duration: int
    reason: str


@dataclass
class ModerationAuditActionResult:
    action_type: str
    reason: str
    addinfo: int


def normalize_reason(reason: str | None) -> str:
    return reason if reason else DEFAULT_REASON


def parse_timeout_duration(duration: int, unit: str) -> int:
    if unit == "분":
        return duration * 60
    if unit == "시간":
        return duration * 3600
    if unit == "일":
        return duration * 86400
    if unit == "주":
        return duration * 604800
    return duration


async def add_warning_action(
    *,
    server_id: int,
    user_id: int,
    admin_id: int,
    amount: int,
    reason: str | None,
    repository=moderation_repository,
):
    result = await repository.add_warning(server_id, user_id, amount)
    warn_max = repository.get_warn_max(server_id)
    normalized_reason = normalize_reason(reason)
    repository.add_blockhistory(user_id, admin_id, normalized_reason, "warn", amount, server_id)
    return WarningActionResult(
        old_count=result.old_count,
        delta=result.delta,
        new_count=result.new_count,
        warn_max=warn_max,
        reason=normalized_reason,
        reached_limit=warn_max is not None and result.new_count >= warn_max,
    )


async def remove_warning_action(
    *,
    server_id: int,
    user_id: int,
    admin_id: int,
    amount: int,
    reason: str | None,
    repository=moderation_repository,
):
    result = await repository.remove_warning(server_id, user_id, amount)
    warn_max = repository.get_warn_max(server_id)
    normalized_reason = normalize_reason(reason)
    repository.add_blockhistory(user_id, admin_id, normalized_reason, "unwarn", amount, server_id)
    return WarningActionResult(
        old_count=result.old_count,
        delta=result.delta,
        new_count=result.new_count,
        warn_max=warn_max,
        reason=normalized_reason,
        reached_limit=False,
    )


async def finalize_warn_limit_ban(
    *,
    server_id: int,
    user_id: int,
    bot_user_id: int,
    repository=moderation_repository,
):
    repository.add_blockhistory(user_id, bot_user_id, "경고 한도 도달", "ban", 0, server_id)
    await repository.reset_warning(server_id, user_id)


def record_timeout_action(
    *,
    server_id: int,
    user_id: int,
    admin_id: int,
    duration: int,
    reason: str | None,
    repository=moderation_repository,
):
    normalized_reason = normalize_reason(reason)
    repository.add_blockhistory(user_id, admin_id, normalized_reason, "timeout", duration, server_id)
    return TimeoutActionResult(duration=duration, reason=normalized_reason)


def record_untimeout_action(
    *,
    server_id: int,
    user_id: int,
    admin_id: int,
    reason: str | None,
    repository=moderation_repository,
):
    normalized_reason = normalize_reason(reason)
    repository.add_blockhistory(user_id, admin_id, normalized_reason, "untimeout", 0, server_id)
    return TimeoutActionResult(duration=0, reason=normalized_reason)


def record_kick_action(
    *,
    server_id: int,
    user_id: int,
    admin_id: int,
    reason: str | None,
    repository=moderation_repository,
):
    normalized_reason = normalize_reason(reason)
    repository.add_blockhistory(user_id, admin_id, normalized_reason, "kick", 0, server_id)
    return ModerationAuditActionResult(action_type="kick", reason=normalized_reason, addinfo=0)


def record_ban_action(
    *,
    server_id: int,
    user_id: int,
    admin_id: int,
    reason: str | None,
    repository=moderation_repository,
):
    normalized_reason = normalize_reason(reason)
    repository.add_blockhistory(user_id, admin_id, normalized_reason, "ban", 0, server_id)
    return ModerationAuditActionResult(action_type="ban", reason=normalized_reason, addinfo=0)


def record_unban_action(
    *,
    server_id: int,
    user_id: int,
    admin_id: int,
    reason: str | None,
    repository=moderation_repository,
):
    normalized_reason = normalize_reason(reason)
    repository.add_blockhistory(user_id, admin_id, normalized_reason, "unban", 0, server_id)
    return ModerationAuditActionResult(action_type="unban", reason=normalized_reason, addinfo=0)


async def get_warning_status(
    *,
    server_id: int,
    user_id: int,
    repository=moderation_repository,
) -> WarningStatusSnapshot:
    warning_count = await repository.get_warning_count(server_id, user_id)
    warn_max = repository.get_warn_max(server_id)
    return WarningStatusSnapshot(warning_count=warning_count, warn_max=warn_max)


def set_warn_limit(
    *,
    server_id: int,
    warn_max: int | None,
    repository=moderation_repository,
) -> WarnLimitSettingResult:
    repository.update_warn_max(server_id, warn_max)
    return WarnLimitSettingResult(warn_max=warn_max)
