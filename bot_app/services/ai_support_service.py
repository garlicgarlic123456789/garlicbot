from __future__ import annotations

import re

from bot_app.repositories.ai_support_repository import ai_support_repository
from bot_app.types.readability_contracts import (
    ChatResetResult,
    EmbedOutputValidationResult,
    LinkScanSnapshot,
    LinkScanStats,
    ModerationLogSnapshot,
    SummaryCooldownResetResult,
)

DISCORD_INVITE_PATTERN = r"(?:d|%64)(?:i|%69)(?:s|%73)(?:c|%63)(?:o|%6f)(?:r|%72)(?:d|%64)(?:app\.com\/invite|(?:\.|%2e)(?:gg|%67%67|com(?::|%3a)?443(?:\/|%2f)?invite))(?:[\/:0-9A-Za-z%\-]*)?"
EMBED_RESERVED_WORDS = ("오류", "경고", "주의", "완료", "성공")


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


def validate_embed_output(
    *,
    title_text: str,
    body_text: str,
    guild_id: int,
    using_server_id: int,
    requester_role_ids: tuple[int, ...],
    spam_whitelist_role_ids: tuple[int, ...],
    raid_keywords: tuple[str, ...],
    automod_keywords: tuple[str, ...],
) -> EmbedOutputValidationResult:
    """Apply legacy slash embed-output validation behind a named result contract."""

    if re.search(DISCORD_INVITE_PATTERN, body_text) or re.search(DISCORD_INVITE_PATTERN, title_text):
        return EmbedOutputValidationResult(status="discord_link")
    if len(title_text) > 256:
        return EmbedOutputValidationResult(status="title_too_long")
    if len(body_text) > 4096:
        return EmbedOutputValidationResult(status="description_too_long")

    if guild_id == using_server_id:
        normalized_title = re.sub(r"[^가-힣a-zA-Z]", "", title_text)
        normalized_body = re.sub(r"[^가-힣a-zA-Z]", "", body_text)

        for raid_keyword in raid_keywords:
            if raid_keyword in normalized_title or raid_keyword in normalized_body:
                return EmbedOutputValidationResult(status="raid_keyword")

        if any(role_id in spam_whitelist_role_ids for role_id in requester_role_ids):
            return EmbedOutputValidationResult(status="ok")

        for automod_keyword in automod_keywords:
            if automod_keyword in normalized_title or automod_keyword in normalized_body:
                return EmbedOutputValidationResult(status="automod_keyword")

    if any(reserved_word in body_text for reserved_word in EMBED_RESERVED_WORDS):
        return EmbedOutputValidationResult(status="reserved_word")
    return EmbedOutputValidationResult(status="ok")


async def scan_link_safety(
    link: str,
    *,
    scan_url,
) -> LinkScanSnapshot:
    """Scan one link and normalize the legacy result dict into named stats."""

    if re.search(DISCORD_INVITE_PATTERN, link):
        return LinkScanSnapshot(status="discord_link")

    raw_result = await scan_url(link)
    if raw_result is None:
        return LinkScanSnapshot(status="scan_error")

    stats = LinkScanStats(
        malicious=raw_result["malicious"],
        suspicious=raw_result["suspicious"],
        harmless=raw_result["harmless"],
        undetected=raw_result["undetected"],
    )

    if stats.malicious > 0:
        severity = "critical"
    elif stats.suspicious >= 3:
        severity = "dangerous"
    elif stats.suspicious > 0:
        severity = "suspicious"
    else:
        severity = "safe"

    return LinkScanSnapshot(status="ok", severity=severity, stats=stats)
