from __future__ import annotations

from bot_app.repositories.ai_support_repository import ai_support_repository
from bot_app.types.readability_contracts import (
    ChatResetResult,
    ModerationLogSnapshot,
    SummaryCooldownResetResult,
)


def reset_chat_history(user_id: int, repository=ai_support_repository) -> ChatResetResult:
    """Clear stored AI conversation thread state for one user."""

    repository.reset_chat_history(user_id)
    return ChatResetResult(status="completed", user_id=user_id, cleared=True)


def load_moderation_log_snapshot(
    server_id: int,
    *,
    target_user_id: int | None = None,
    admin_id: int | None = None,
    include_legacy: bool = False,
    repository=ai_support_repository,
) -> ModerationLogSnapshot:
    """Load moderation log rows behind a named snapshot contract."""

    entries = repository.load_moderation_log_entries(
        server_id,
        target_user_id=target_user_id,
        admin_id=admin_id,
        include_legacy=include_legacy,
    )
    current_entry_count = sum(1 for entry in entries if entry.source_table == "blockhistory")
    legacy_entry_count = sum(1 for entry in entries if entry.source_table == "blockhistory_old")
    return ModerationLogSnapshot(
        status="found" if entries else "missing",
        server_id=server_id,
        entries=entries,
        target_user_id=target_user_id,
        admin_id=admin_id,
        include_legacy=include_legacy,
        current_entry_count=current_entry_count,
        legacy_entry_count=legacy_entry_count,
    )


def clear_summary_cooldown(
    user_id: int,
    cooldown_store,
) -> SummaryCooldownResetResult:
    """Clear summarize cooldown state without exposing raw dict mutation to callers."""

    if user_id in cooldown_store:
        del cooldown_store[user_id]
        return SummaryCooldownResetResult(status="cleared", user_id=user_id, removed=True)
    return SummaryCooldownResetResult(status="missing", user_id=user_id, removed=False)
