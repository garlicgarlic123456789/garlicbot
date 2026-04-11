from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

import discord

from bot_app.repositories.security_repository import (
    AntiNukeSettingRecord,
    DeveloperRestrictionRecord,
    SecurityCommandPermission,
    security_repository,
)
from bot_app.types.readability_contracts import AutomodConfig, AutomodRuleConfig, UserBlockState


DeveloperRestrictionMutationStatus = Literal["added", "removed", "missing"]


@dataclass(frozen=True, slots=True)
class DeveloperRestrictionMutationResult:
    status: DeveloperRestrictionMutationStatus
    user_id: int
    reason: str | None = None
    until: str | None = None


@dataclass(frozen=True, slots=True)
class GuildSecurityActionResult:
    dm_disabled_until: datetime | None
    invites_disabled_until: datetime | None
    audit_reason: str


def get_developer_restriction_state(user, repository=security_repository) -> UserBlockState:
    """Interpret stored developer restriction JSON as a named block-state contract."""
    restriction = repository.get_developer_restriction(user.id)
    if restriction is None:
        return UserBlockState(status="not_blocked")

    try:
        blocked_until = datetime.strptime(restriction.until or "", "%Y-%m-%d").date()
    except ValueError:
        return UserBlockState(status="not_blocked")

    if datetime.today().date() > blocked_until:
        return UserBlockState(status="not_blocked")

    return UserBlockState(
        status="blocked",
        blocked_until_label=restriction.until,
        reason=restriction.reason,
    )


def add_developer_restriction(user_id: int, *, reason: str, until: str, repository=security_repository) -> DeveloperRestrictionMutationResult:
    """Persist the developer-only command restriction JSON entry via the repository boundary."""
    restriction = DeveloperRestrictionRecord(user_id=user_id, reason=reason, until=until)
    repository.add_developer_restriction(restriction)
    return DeveloperRestrictionMutationResult(
        status="added",
        user_id=user_id,
        reason=reason,
        until=until,
    )


def remove_developer_restriction(user_id: int, repository=security_repository) -> DeveloperRestrictionMutationResult:
    removed = repository.remove_developer_restriction(user_id)
    return DeveloperRestrictionMutationResult(
        status="removed" if removed else "missing",
        user_id=user_id,
    )


async def apply_guild_security_action(
    guild,
    *,
    actor,
    reason: str,
    dm_disabled_seconds: int,
    invite_disabled_seconds: int,
) -> GuildSecurityActionResult:
    """Apply /보안조치-style guild lock settings while returning explicit computed values."""
    now = discord.utils.utcnow()
    dm_disabled_until = None if dm_disabled_seconds <= 0 else now + timedelta(seconds=dm_disabled_seconds)
    invites_disabled_until = None if invite_disabled_seconds <= 0 else now + timedelta(seconds=invite_disabled_seconds)
    audit_reason = f"{actor.display_name} ({actor.id}) 의 /보안조치 명령어 사용 (사유: {reason})"

    await guild.edit(
        dms_disabled_until=dm_disabled_until,
        invites_disabled_until=invites_disabled_until,
        reason=audit_reason,
    )

    return GuildSecurityActionResult(
        dm_disabled_until=dm_disabled_until,
        invites_disabled_until=invites_disabled_until,
        audit_reason=audit_reason,
    )


def update_channel_command_permission(
    *,
    server_id: int,
    command_name: str,
    channel_id: int,
    target_kind: Literal["role", "user"],
    permitted,
    role_id: int | None = None,
    user_id: int | None = None,
    repository=security_repository,
) -> SecurityCommandPermission:
    permission = SecurityCommandPermission(
        server_id=server_id,
        command_name=command_name,
        channel_id=channel_id,
        target_kind=target_kind,
        role_id=role_id,
        user_id=user_id,
        permitted=permitted,
    )
    repository.update_channel_command_permission(permission)
    return permission


def update_server_command_permission(
    *,
    server_id: int,
    command_name: str,
    target_kind: Literal["role", "user"],
    permitted,
    role_id: int | None = None,
    user_id: int | None = None,
    repository=security_repository,
) -> SecurityCommandPermission:
    permission = SecurityCommandPermission(
        server_id=server_id,
        command_name=command_name,
        target_kind=target_kind,
        role_id=role_id,
        user_id=user_id,
        permitted=permitted,
    )
    repository.update_server_command_permission(permission)
    return permission


def update_automod_exception_channel_setting(
    *,
    server_id: int,
    channel_id: int,
    enabled: bool,
    repository=security_repository,
) -> bool:
    repository.update_automod_exception_channel_setting(server_id, channel_id, enabled)
    return enabled


def update_automod_setting(
    *,
    server_id: int,
    political: AutomodRuleConfig,
    sexual: AutomodRuleConfig,
    invite_link: AutomodRuleConfig,
    mention: AutomodRuleConfig,
    whitelist_permission,
    repository=security_repository,
) -> AutomodConfig:
    config = AutomodConfig(
        political=political,
        sexual=sexual,
        invite_link=invite_link,
        mention=mention,
        whitelist_permission=whitelist_permission,
    )
    repository.update_automod_setting(server_id, config)
    return config


def update_quarantine_role_setting(*, server_id: int, role_id: int, repository=security_repository) -> int:
    repository.update_quarantine_role_setting(server_id, role_id)
    return role_id


def get_quarantine_role_id(server_id: int, repository=security_repository) -> int | None:
    return repository.get_quarantine_role_id(server_id)


def update_anti_nuke_setting(
    *,
    server_id: int,
    enabled: bool,
    log_channel_id: int | None,
    repository=security_repository,
) -> AntiNukeSettingRecord:
    setting = AntiNukeSettingRecord(
        server_id=server_id,
        enabled=enabled,
        log_channel_id=log_channel_id,
    )
    repository.update_anti_nuke_setting(setting)
    return setting


def update_anti_nuke_whitelist_setting(
    *,
    server_id: int,
    user_id: int,
    enabled: bool,
    repository=security_repository,
) -> bool:
    repository.update_anti_nuke_whitelist_setting(server_id, user_id, enabled)
    return enabled
