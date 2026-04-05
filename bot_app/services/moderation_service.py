from dataclasses import dataclass

from bot_app.repositories import moderation_repository


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
        old_count=result[0],
        delta=result[1],
        new_count=result[2],
        warn_max=warn_max,
        reason=normalized_reason,
        reached_limit=warn_max is not None and result[2] >= warn_max,
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
        old_count=result[0],
        delta=result[1],
        new_count=result[2],
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
