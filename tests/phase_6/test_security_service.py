from __future__ import annotations

from datetime import datetime, timedelta
from importlib import import_module
from types import SimpleNamespace

import pytest

from bot_app.repositories.security_repository import (
    AntiNukeSettingRecord,
    DeveloperRestrictionRecord,
    SecurityCommandPermission,
    SecurityRepository,
)
from bot_app.services.security_service import (
    DeveloperRestrictionMutationResult,
    GuildSecurityActionResult,
    add_developer_restriction,
    apply_guild_security_action,
    get_developer_restriction_state,
    get_quarantine_role_id,
    remove_developer_restriction,
    update_anti_nuke_setting,
    update_anti_nuke_whitelist_setting,
    update_automod_exception_channel_setting,
    update_automod_setting,
    update_channel_command_permission,
    update_quarantine_role_setting,
    update_server_command_permission,
)
from bot_app.types.readability_contracts import AutomodConfig, AutomodRuleConfig, UserBlockState


class FakeSecurityRepository:
    def __init__(self):
        self.calls = []
        self.restriction = None
        self.quarantine_role_id = None

    def get_developer_restriction(self, user_id: int):
        self.calls.append(("get_developer_restriction", user_id))
        return self.restriction

    def add_developer_restriction(self, record: DeveloperRestrictionRecord):
        self.calls.append(("add_developer_restriction", record))

    def remove_developer_restriction(self, user_id: int) -> bool:
        self.calls.append(("remove_developer_restriction", user_id))
        return user_id == 10

    def update_channel_command_permission(self, permission: SecurityCommandPermission):
        self.calls.append(("update_channel_command_permission", permission))

    def update_server_command_permission(self, permission: SecurityCommandPermission):
        self.calls.append(("update_server_command_permission", permission))

    def update_automod_exception_channel_setting(self, server_id: int, channel_id: int, enabled: bool):
        self.calls.append(("update_automod_exception_channel_setting", server_id, channel_id, enabled))

    def update_automod_setting(self, server_id: int, config: AutomodConfig):
        self.calls.append(("update_automod_setting", server_id, config))

    def update_quarantine_role_setting(self, server_id: int, role_id: int):
        self.calls.append(("update_quarantine_role_setting", server_id, role_id))

    def get_quarantine_role_id(self, server_id: int):
        self.calls.append(("get_quarantine_role_id", server_id))
        return self.quarantine_role_id

    def update_anti_nuke_setting(self, setting: AntiNukeSettingRecord):
        self.calls.append(("update_anti_nuke_setting", setting))

    def update_anti_nuke_whitelist_setting(self, server_id: int, user_id: int, enabled: bool):
        self.calls.append(("update_anti_nuke_whitelist_setting", server_id, user_id, enabled))


def test_security_repository_delegates_to_legacy_helpers_and_storage(monkeypatch):
    security_repository_module = import_module("bot_app.repositories.security_repository")
    calls = []
    stored_restrictions = {"10": {"reason": "스팸", "until": "2099-01-01"}}

    monkeypatch.setattr(security_repository_module, "get_quarantine_role", lambda server_id: calls.append(("get_quarantine_role", server_id)) or 1234)
    monkeypatch.setattr(security_repository_module, "update_quarantine_role", lambda server_id, role_id: calls.append(("update_quarantine_role", server_id, role_id)))
    monkeypatch.setattr(security_repository_module, "get_automod_exception_channel", lambda server_id, channel_id: calls.append(("get_automod_exception_channel", server_id, channel_id)) or True)
    monkeypatch.setattr(security_repository_module, "update_automod_exception_channel", lambda server_id, channel_id, enabled: calls.append(("update_automod_exception_channel", server_id, channel_id, enabled)))
    monkeypatch.setattr(security_repository_module, "get_server_perm", lambda server_id, command_name, role_id, user_id: calls.append(("get_server_perm", server_id, command_name, role_id, user_id)) or "allow")
    monkeypatch.setattr(security_repository_module, "update_server_perm", lambda server_id, command_name, target_kind, role_id, user_id, permitted: calls.append(("update_server_perm", server_id, command_name, target_kind, role_id, user_id, permitted)))
    monkeypatch.setattr(security_repository_module, "get_channel_perm", lambda server_id, command_name, channel_id, role_id, user_id: calls.append(("get_channel_perm", server_id, command_name, channel_id, role_id, user_id)) or "deny")
    monkeypatch.setattr(security_repository_module, "update_channel_perm", lambda server_id, command_name, channel_id, target_kind, role_id, user_id, permitted: calls.append(("update_channel_perm", server_id, command_name, channel_id, target_kind, role_id, user_id, permitted)))
    monkeypatch.setattr(
        security_repository_module,
        "get_automod",
        lambda server_id: calls.append(("get_automod", server_id)) or {
            "political": [True, 10],
            "sexual": [False, 0],
            "invite_link": [True, 60],
            "mention": [False, 0],
            "whitelist_permission": "manage_messages",
        },
    )
    monkeypatch.setattr(security_repository_module, "update_automod", lambda server_id, political, sexual, invite_link, mention, whitelist_permission: calls.append(("update_automod", server_id, political, sexual, invite_link, mention, whitelist_permission)))
    monkeypatch.setattr(security_repository_module, "get_anti_nuke_option", lambda server_id: calls.append(("get_anti_nuke_option", server_id)) or True)
    monkeypatch.setattr(security_repository_module, "get_anti_nuke_log_channel", lambda server_id: calls.append(("get_anti_nuke_log_channel", server_id)) or 777)
    monkeypatch.setattr(security_repository_module, "update_anti_nuke_option", lambda server_id, enabled: calls.append(("update_anti_nuke_option", server_id, enabled)))
    monkeypatch.setattr(security_repository_module, "update_anti_nuke_log_channel", lambda server_id, channel_id: calls.append(("update_anti_nuke_log_channel", server_id, channel_id)))
    monkeypatch.setattr(security_repository_module, "get_anti_nuke_whitelist", lambda server_id, user_id: calls.append(("get_anti_nuke_whitelist", server_id, user_id)) or False)
    monkeypatch.setattr(security_repository_module, "update_anti_nuke_whitelist", lambda server_id, user_id, enabled: calls.append(("update_anti_nuke_whitelist", server_id, user_id, enabled)))
    monkeypatch.setattr(security_repository_module, "load_command_blocked_users", lambda path: calls.append(("load_command_blocked_users", path)) or dict(stored_restrictions))
    monkeypatch.setattr(security_repository_module, "save_command_blocked_users", lambda path, data: calls.append(("save_command_blocked_users", path, data)))

    repository = SecurityRepository()

    automod_config = repository.get_automod_setting(1)
    repository.update_automod_setting(1, automod_config)
    anti_nuke_setting = repository.get_anti_nuke_setting(1)
    repository.update_anti_nuke_setting(anti_nuke_setting)
    assert repository.get_quarantine_role_id(1) == 1234
    repository.update_quarantine_role_setting(1, 555)
    assert repository.is_automod_exception_channel(1, 20) is True
    repository.update_automod_exception_channel_setting(1, 20, False)
    assert repository.get_server_command_permission(1, "서버명령", role_id=30, user_id=None) == "allow"
    repository.update_server_command_permission(
        SecurityCommandPermission(server_id=1, command_name="서버명령", target_kind="role", role_id=30, user_id=None, permitted=True),
    )
    assert repository.get_channel_command_permission(1, "채널명령", 40, role_id=None, user_id=50) == "deny"
    repository.update_channel_command_permission(
        SecurityCommandPermission(server_id=1, command_name="채널명령", channel_id=40, target_kind="user", role_id=None, user_id=50, permitted=False),
    )
    assert repository.get_anti_nuke_whitelist_setting(1, 60) is False
    repository.update_anti_nuke_whitelist_setting(1, 60, True)
    assert repository.get_developer_restriction(10) == DeveloperRestrictionRecord(user_id=10, reason="스팸", until="2099-01-01")
    repository.add_developer_restriction(DeveloperRestrictionRecord(user_id=11, reason="도배", until="2099-02-01"))
    assert repository.remove_developer_restriction(10) is True
    assert repository.remove_developer_restriction(999) is False

    assert automod_config == AutomodConfig(
        political=AutomodRuleConfig(enabled=True, action=10),
        sexual=AutomodRuleConfig(enabled=False, action=0),
        invite_link=AutomodRuleConfig(enabled=True, action=60),
        mention=AutomodRuleConfig(enabled=False, action=0),
        whitelist_permission="manage_messages",
    )
    assert anti_nuke_setting == AntiNukeSettingRecord(server_id=1, enabled=True, log_channel_id=777)
    assert calls == [
        ("get_automod", 1),
        ("update_automod", 1, [True, 10], [False, 0], [True, 60], [False, 0], "manage_messages"),
        ("get_anti_nuke_option", 1),
        ("get_anti_nuke_log_channel", 1),
        ("update_anti_nuke_option", 1, True),
        ("update_anti_nuke_log_channel", 1, 777),
        ("get_quarantine_role", 1),
        ("update_quarantine_role", 1, 555),
        ("get_automod_exception_channel", 1, 20),
        ("update_automod_exception_channel", 1, 20, False),
        ("get_server_perm", 1, "서버명령", 30, None),
        ("update_server_perm", 1, "서버명령", "role", 30, None, True),
        ("get_channel_perm", 1, "채널명령", 40, None, 50),
        ("update_channel_perm", 1, "채널명령", 40, "user", None, 50, False),
        ("get_anti_nuke_whitelist", 1, 60),
        ("update_anti_nuke_whitelist", 1, 60, True),
        ("load_command_blocked_users", "command_blocked_user.json"),
        ("load_command_blocked_users", "command_blocked_user.json"),
        ("save_command_blocked_users", "command_blocked_user.json", {"10": {"reason": "스팸", "until": "2099-01-01"}, "11": {"reason": "도배", "until": "2099-02-01"}}),
        ("load_command_blocked_users", "command_blocked_user.json"),
        ("save_command_blocked_users", "command_blocked_user.json", {}),
        ("load_command_blocked_users", "command_blocked_user.json"),
    ]


def test_get_developer_restriction_state_returns_named_block_state():
    repository = FakeSecurityRepository()
    user = SimpleNamespace(id=10)

    assert get_developer_restriction_state(user, repository=repository) == UserBlockState(status="not_blocked")

    repository.restriction = DeveloperRestrictionRecord(user_id=10, reason="테스트", until="not-a-date")
    assert get_developer_restriction_state(user, repository=repository) == UserBlockState(status="not_blocked")

    repository.restriction = DeveloperRestrictionRecord(user_id=10, reason="만료", until="2000-01-01")
    assert get_developer_restriction_state(user, repository=repository) == UserBlockState(status="not_blocked")

    repository.restriction = DeveloperRestrictionRecord(user_id=10, reason="활성", until="2099-01-01")
    assert get_developer_restriction_state(user, repository=repository) == UserBlockState(
        status="blocked",
        blocked_until_label="2099-01-01",
        reason="활성",
    )


def test_developer_restriction_mutations_return_named_results():
    repository = FakeSecurityRepository()

    added = add_developer_restriction(10, reason="남용", until="2099-05-01", repository=repository)
    removed = remove_developer_restriction(10, repository=repository)
    missing = remove_developer_restriction(999, repository=repository)

    assert added == DeveloperRestrictionMutationResult(
        status="added",
        user_id=10,
        reason="남용",
        until="2099-05-01",
    )
    assert removed == DeveloperRestrictionMutationResult(status="removed", user_id=10)
    assert missing == DeveloperRestrictionMutationResult(status="missing", user_id=999)
    assert repository.calls == [
        ("add_developer_restriction", DeveloperRestrictionRecord(user_id=10, reason="남용", until="2099-05-01")),
        ("remove_developer_restriction", 10),
        ("remove_developer_restriction", 999),
    ]


@pytest.mark.asyncio
async def test_apply_guild_security_action_builds_until_values_and_reason(monkeypatch):
    security_service_module = import_module("bot_app.services.security_service")
    fixed_now = datetime(2026, 4, 7, 12, 0, 0)
    monkeypatch.setattr(security_service_module.discord.utils, "utcnow", lambda: fixed_now)

    captured = {}

    class FakeGuild:
        async def edit(self, *, dms_disabled_until, invites_disabled_until, reason):
            captured["dms_disabled_until"] = dms_disabled_until
            captured["invites_disabled_until"] = invites_disabled_until
            captured["reason"] = reason

    actor = SimpleNamespace(display_name="관리자", id=77)

    result = await apply_guild_security_action(
        FakeGuild(),
        actor=actor,
        reason="점검",
        dm_disabled_seconds=60,
        invite_disabled_seconds=0,
    )

    assert result == GuildSecurityActionResult(
        dm_disabled_until=fixed_now + timedelta(seconds=60),
        invites_disabled_until=None,
        audit_reason="관리자 (77) 의 /보안조치 명령어 사용 (사유: 점검)",
    )
    assert captured == {
        "dms_disabled_until": fixed_now + timedelta(seconds=60),
        "invites_disabled_until": None,
        "reason": "관리자 (77) 의 /보안조치 명령어 사용 (사유: 점검)",
    }


def test_security_service_update_helpers_return_named_contracts():
    repository = FakeSecurityRepository()

    channel_permission = update_channel_command_permission(
        server_id=1,
        command_name="공지",
        channel_id=20,
        target_kind="user",
        user_id=30,
        permitted=False,
        repository=repository,
    )
    server_permission = update_server_command_permission(
        server_id=1,
        command_name="공지",
        target_kind="role",
        role_id=40,
        permitted=True,
        repository=repository,
    )
    assert update_automod_exception_channel_setting(server_id=1, channel_id=20, enabled=True, repository=repository) is True

    automod_config = update_automod_setting(
        server_id=1,
        political=AutomodRuleConfig(enabled=True, action=10),
        sexual=AutomodRuleConfig(enabled=False, action=0),
        invite_link=AutomodRuleConfig(enabled=True, action=60),
        mention=AutomodRuleConfig(enabled=False, action=0),
        whitelist_permission="admin",
        repository=repository,
    )
    assert update_quarantine_role_setting(server_id=1, role_id=55, repository=repository) == 55
    repository.quarantine_role_id = 55
    assert get_quarantine_role_id(1, repository=repository) == 55
    anti_nuke_setting = update_anti_nuke_setting(server_id=1, enabled=True, log_channel_id=70, repository=repository)
    assert update_anti_nuke_whitelist_setting(server_id=1, user_id=80, enabled=False, repository=repository) is False

    assert channel_permission == SecurityCommandPermission(
        server_id=1,
        command_name="공지",
        channel_id=20,
        target_kind="user",
        role_id=None,
        user_id=30,
        permitted=False,
    )
    assert server_permission == SecurityCommandPermission(
        server_id=1,
        command_name="공지",
        target_kind="role",
        role_id=40,
        user_id=None,
        permitted=True,
    )
    assert automod_config == AutomodConfig(
        political=AutomodRuleConfig(enabled=True, action=10),
        sexual=AutomodRuleConfig(enabled=False, action=0),
        invite_link=AutomodRuleConfig(enabled=True, action=60),
        mention=AutomodRuleConfig(enabled=False, action=0),
        whitelist_permission="admin",
    )
    assert anti_nuke_setting == AntiNukeSettingRecord(server_id=1, enabled=True, log_channel_id=70)
    assert repository.calls == [
        ("update_channel_command_permission", channel_permission),
        ("update_server_command_permission", server_permission),
        ("update_automod_exception_channel_setting", 1, 20, True),
        ("update_automod_setting", 1, automod_config),
        ("update_quarantine_role_setting", 1, 55),
        ("get_quarantine_role_id", 1),
        ("update_anti_nuke_setting", anti_nuke_setting),
        ("update_anti_nuke_whitelist_setting", 1, 80, False),
    ]
