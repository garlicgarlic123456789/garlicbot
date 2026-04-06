from __future__ import annotations

from typing import Mapping

from commands.return_level import return_level

from bot_app.repositories.user_repository import user_repository
from bot_app.repositories.xp_repository import xp_repository
from bot_app.services.xp_service import get_effective_xp_setting
from bot_app.types.readability_contracts import (
    DisplayedXpSnapshot,
    UserMoneyLookupResult,
    UserProfileSnapshot,
)


def get_user_money_lookup(user_id: int, repository=user_repository) -> UserMoneyLookupResult:
    """Return whether a user money row exists and its current balance."""
    money = repository.get_user_money(user_id)
    if money is None:
        return UserMoneyLookupResult(status="missing")
    return UserMoneyLookupResult(status="found", money=money)


async def get_user_warning_count(
    *,
    server_id: int,
    user_id: int,
    repository=user_repository,
) -> int:
    return await repository.get_warning_count(server_id, user_id)


def get_user_classification(
    *,
    user,
    block_checker,
    repository=user_repository,
) -> tuple[str, str]:
    """Resolve the displayed user classification while preserving legacy wording."""
    status, until, reason = block_checker(user)
    if status:
        return "blocked", f"이용제한 유저 ({until}까지, 사유: {reason})"
    if repository.has_premium(user.id):
        return "premium", "프리미엄 유저"
    return "general", "일반 유저"


def get_displayed_profile_xp_snapshot(
    *,
    server_id: int,
    user_id: int,
    xp_settings: Mapping[int, object],
    xp_setting_repository=xp_repository,
    xp_data_repository=xp_repository,
    leveler=return_level,
) -> DisplayedXpSnapshot | None:
    """Match the legacy /사용자정보 XP display contract."""
    xp_setting = get_effective_xp_setting(
        server_id=server_id,
        xp_settings=xp_settings,
        repository=xp_setting_repository,
    )
    if xp_setting.enabled is False:
        return None

    total_xp = xp_data_repository.get_xp(server_id, user_id)
    displayed_month_xp = xp_data_repository.get_xp(server_id, user_id)
    return DisplayedXpSnapshot(
        total_xp=total_xp,
        displayed_month_xp=displayed_month_xp,
        total_level=leveler(total_xp),
        displayed_month_level=leveler(displayed_month_xp),
        unit=xp_setting.unit,
    )


def build_user_profile_snapshot(
    *,
    source: str,
    user,
    role_mentions: tuple[str, ...],
    xp_snapshot: DisplayedXpSnapshot | None,
    account_created_at_label: str,
    joined_at_label: str | None,
    warning_count: int,
    restriction_status_label: str,
    classification_status: str,
    classification_label: str,
) -> UserProfileSnapshot:
    """Build the named profile snapshot consumed by the slash handler."""
    return UserProfileSnapshot(
        source=source,
        user_id=user.id,
        display_name=user.display_name,
        mention=f"<@{user.id}>",
        role_mentions=role_mentions,
        xp_snapshot=xp_snapshot,
        account_created_at_label=account_created_at_label,
        joined_at_label=joined_at_label,
        warning_count=warning_count,
        restriction_status_label=restriction_status_label,
        classification_status=classification_status,
        classification_label=classification_label,
        avatar_url=user.display_avatar.url,
    )
