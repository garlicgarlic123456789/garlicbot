from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from commands.database import (
    get_anti_nuke_log_channel,
    get_anti_nuke_option,
    get_anti_nuke_whitelist,
    get_automod,
    get_automod_exception_channel,
    get_channel_perm,
    get_quarantine_role,
    get_server_perm,
    update_anti_nuke_log_channel,
    update_anti_nuke_option,
    update_anti_nuke_whitelist,
    update_automod,
    update_automod_exception_channel,
    update_channel_perm,
    update_quarantine_role,
    update_server_perm,
)
from bot_app.config.constants import BLOCKED_USERS_FILE
from bot_app.services.storage_service import load_command_blocked_users, save_command_blocked_users
from bot_app.types.readability_contracts import AutomodConfig, AutomodRuleConfig


PermissionTargetKind = Literal["role", "user"]


@dataclass(frozen=True, slots=True)
class DeveloperRestrictionRecord:
    user_id: int
    reason: str | None
    until: str | None


@dataclass(frozen=True, slots=True)
class SecurityCommandPermission:
    server_id: int
    command_name: str
    target_kind: PermissionTargetKind
    permitted: Any
    role_id: int | None = None
    user_id: int | None = None
    channel_id: int | None = None


@dataclass(frozen=True, slots=True)
class AntiNukeSettingRecord:
    server_id: int
    enabled: bool
    log_channel_id: int | None


def _build_rule_config(raw_rule: list | tuple) -> AutomodRuleConfig:
    enabled, action = raw_rule
    return AutomodRuleConfig(enabled=enabled, action=action)


def _build_automod_config(raw: dict[str, Any]) -> AutomodConfig:
    return AutomodConfig(
        political=_build_rule_config(raw["political"]),
        sexual=_build_rule_config(raw["sexual"]),
        invite_link=_build_rule_config(raw["invite_link"]),
        mention=_build_rule_config(raw["mention"]),
        whitelist_permission=raw["whitelist_permission"],
    )


def _serialize_rule_config(rule: AutomodRuleConfig) -> list[int | bool]:
    return [rule.enabled, rule.action]


class SecurityRepository:
    def get_quarantine_role_id(self, server_id: int) -> int | None:
        return get_quarantine_role(server_id)

    def update_quarantine_role_setting(self, server_id: int, role_id: int):
        update_quarantine_role(server_id, role_id)

    def is_automod_exception_channel(self, server_id: int, channel_id: int) -> bool:
        return get_automod_exception_channel(server_id, channel_id)

    def update_automod_exception_channel_setting(self, server_id: int, channel_id: int, enabled: bool):
        update_automod_exception_channel(server_id, channel_id, enabled)

    def get_server_command_permission(
        self,
        server_id: int,
        command_name: str,
        *,
        role_id: int | None,
        user_id: int | None,
    ):
        return get_server_perm(server_id, command_name, role_id, user_id)

    def update_server_command_permission(self, permission: SecurityCommandPermission):
        update_server_perm(
            permission.server_id,
            permission.command_name,
            permission.target_kind,
            permission.role_id,
            permission.user_id,
            permission.permitted,
        )

    def get_channel_command_permission(
        self,
        server_id: int,
        command_name: str,
        channel_id: int,
        *,
        role_id: int | None,
        user_id: int | None,
    ):
        return get_channel_perm(server_id, command_name, channel_id, role_id, user_id)

    def update_channel_command_permission(self, permission: SecurityCommandPermission):
        update_channel_perm(
            permission.server_id,
            permission.command_name,
            permission.channel_id,
            permission.target_kind,
            permission.role_id,
            permission.user_id,
            permission.permitted,
        )

    def get_automod_setting(self, server_id: int) -> AutomodConfig:
        return _build_automod_config(get_automod(server_id))

    def update_automod_setting(self, server_id: int, config: AutomodConfig):
        update_automod(
            server_id,
            _serialize_rule_config(config.political),
            _serialize_rule_config(config.sexual),
            _serialize_rule_config(config.invite_link),
            _serialize_rule_config(config.mention),
            config.whitelist_permission,
        )

    def get_anti_nuke_setting(self, server_id: int) -> AntiNukeSettingRecord:
        return AntiNukeSettingRecord(
            server_id=server_id,
            enabled=get_anti_nuke_option(server_id),
            log_channel_id=get_anti_nuke_log_channel(server_id),
        )

    def update_anti_nuke_setting(self, setting: AntiNukeSettingRecord):
        update_anti_nuke_option(setting.server_id, setting.enabled)
        update_anti_nuke_log_channel(setting.server_id, setting.log_channel_id)

    def get_anti_nuke_whitelist_setting(self, server_id: int, user_id: int) -> bool:
        return get_anti_nuke_whitelist(server_id, user_id)

    def update_anti_nuke_whitelist_setting(self, server_id: int, user_id: int, enabled: bool):
        update_anti_nuke_whitelist(server_id, user_id, enabled)

    def load_developer_restrictions(self) -> dict[str, dict[str, Any]]:
        return load_command_blocked_users(BLOCKED_USERS_FILE)

    def save_developer_restrictions(self, data: dict[str, dict[str, Any]]):
        save_command_blocked_users(BLOCKED_USERS_FILE, data)

    def get_developer_restriction(self, user_id: int) -> DeveloperRestrictionRecord | None:
        raw_restrictions = self.load_developer_restrictions()
        raw_record = raw_restrictions.get(str(user_id))
        if raw_record is None:
            return None
        return DeveloperRestrictionRecord(
            user_id=user_id,
            reason=raw_record.get("reason"),
            until=raw_record.get("until"),
        )

    def add_developer_restriction(self, record: DeveloperRestrictionRecord):
        raw_restrictions = self.load_developer_restrictions()
        raw_restrictions[str(record.user_id)] = {
            "reason": record.reason,
            "until": record.until,
        }
        self.save_developer_restrictions(raw_restrictions)

    def remove_developer_restriction(self, user_id: int) -> bool:
        raw_restrictions = self.load_developer_restrictions()
        key = str(user_id)
        if key not in raw_restrictions:
            return False
        del raw_restrictions[key]
        self.save_developer_restrictions(raw_restrictions)
        return True


security_repository = SecurityRepository()
