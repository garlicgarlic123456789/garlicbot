from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

import bot_app.commands.slash_admin_support_handlers as handlers_module
from bot_app.commands.slash_admin_support_handlers import (
    run_add_blockhistory_entry_slash_command,
    run_backup_channel_slash_command,
    run_check_invite_route_slash_command,
    run_check_user_join_route_slash_command,
    run_delete_blockhistory_entry_slash_command,
    run_developer_command_slash_command,
    run_resolve_post_slash_command,
    run_restore_channel_slash_command,
    run_role_info_slash_command,
    run_set_invite_route_memo_slash_command,
    run_set_user_join_route_slash_command,
    run_update_role_description_slash_command,
)
from bot_app.types.readability_contracts import ChannelBackupLookupResult, ChannelBackupManifest, ChannelBackupMessage, InviteRouteEntry, InviteRouteReport, SlashCommandResult


class FakeResponse:
    def __init__(self):
        self.deferred = []
        self.sent = []

    async def defer(self, *, ephemeral=False):
        self.deferred.append({"ephemeral": ephemeral})

    async def send_message(self, content=None, *, embed=None, ephemeral=False):
        self.sent.append({"content": content, "embed": embed, "ephemeral": ephemeral})


class FakeFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, content=None, *, embed=None, ephemeral=False):
        self.sent.append({"content": content, "embed": embed, "ephemeral": ephemeral})


class FakeUser:
    def __init__(self, user_id: int, *, display_name="사용자", mention=None, guild_permissions=None):
        self.id = user_id
        self.display_name = display_name
        self.mention = mention or f"<@{user_id}>"
        self.guild_permissions = guild_permissions or SimpleNamespace(manage_roles=False)

    async def send(self, content=None, *, file=None):
        self.sent = {"content": content, "file": file}


class FakeParentForum:
    def __init__(self, forum_id: int):
        self.id = forum_id
        self.tags = {}

    def get_tag(self, tag_id: int):
        return self.tags[tag_id]


class FakeThread:
    def __init__(self, parent):
        self.parent = parent
        self.edits = []

    async def edit(self, *, applied_tags=None, reason=None):
        self.edits.append({"applied_tags": applied_tags, "reason": reason})


class FakeInteraction:
    def __init__(self, *, user, guild=None, channel=None):
        self.user = user
        self.guild = guild
        self.channel = channel
        self.response = FakeResponse()
        self.followup = FakeFollowup()


class FakeRole:
    def __init__(self, role_id: int, name="역할", color="#ffffff", mention=None):
        self.id = role_id
        self.name = name
        self.color = color
        self.mention = mention or f"<@&{role_id}>"
        self.members = []


class FakeHistoryChannel:
    def __init__(self, messages):
        self._messages = list(messages)

    async def history(self, *, limit):
        for message in self._messages[:limit]:
            yield message


class FakeAttachment:
    def __init__(self, filename: str, url: str):
        self.filename = filename
        self.url = url


class FakeMessage:
    def __init__(self, author_id: int, content: str, attachments=None):
        self.author = SimpleNamespace(id=author_id)
        self.content = content
        self.attachments = list(attachments or [])


class FakeWebhook:
    def __init__(self):
        self.sent = []

    async def send(self, **kwargs):
        self.sent.append(kwargs)


class FakeRestoreChannel:
    def __init__(self):
        self.webhooks = []

    async def create_webhook(self, *, name: str):
        webhook = FakeWebhook()
        self.webhooks.append({"name": name, "webhook": webhook})
        return webhook


@pytest.mark.asyncio
async def test_resolve_post_helper_rejects_wrong_channel():
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1), channel=SimpleNamespace())

    result = await run_resolve_post_slash_command(
        interaction,
        resolved=True,
        reason_text="테스트",
        context={
            "is_blocked": lambda user: (False, None, None),
            "forum_parent_id": 1,
            "resolved_tag_id": 10,
            "unresolved_tag_id": 20,
        },
    )

    assert result == SlashCommandResult(status="rejected", reason_code="invalid_channel")
    assert interaction.followup.sent[0]["embed"].description == "이 명령어는 특정 채널에서만 사용 가능합니다."


@pytest.mark.asyncio
async def test_resolve_post_helper_updates_thread_tags():
    parent = FakeParentForum(100)
    parent.tags[1] = "resolved-tag"
    parent.tags[2] = "unresolved-tag"
    original_thread_class = handlers_module.discord.Thread
    handlers_module.discord.Thread = FakeThread
    interaction = FakeInteraction(
        user=FakeUser(10, display_name="마늘"),
        guild=SimpleNamespace(id=1),
        channel=FakeThread(parent),
    )
    try:
        result = await run_resolve_post_slash_command(
            interaction,
            resolved=False,
            reason_text="추가 답변 필요",
            context={
                "is_blocked": lambda user: (False, None, None),
                "forum_parent_id": 100,
                "resolved_tag_id": 1,
                "unresolved_tag_id": 2,
            },
        )
    finally:
        handlers_module.discord.Thread = original_thread_class

    assert result == SlashCommandResult(status="completed", reason_code="issue_resolution_updated")
    assert interaction.channel.edits[0]["applied_tags"] == ["unresolved-tag"]
    assert "답변 필요 상태" in interaction.followup.sent[0]["embed"].description


@pytest.mark.asyncio
async def test_update_role_description_helper_validates_permission_and_length(monkeypatch):
    interaction = FakeInteraction(
        user=FakeUser(10, guild_permissions=SimpleNamespace(manage_roles=False)),
        guild=SimpleNamespace(id=1),
    )

    result = await run_update_role_description_slash_command(
        interaction,
        role=FakeRole(1),
        description="테스트",
        context={"is_blocked": lambda user: (False, None, None)},
    )

    assert result == SlashCommandResult(status="rejected", reason_code="missing_manage_roles_permission")

    interaction = FakeInteraction(
        user=FakeUser(10, guild_permissions=SimpleNamespace(manage_roles=True)),
        guild=SimpleNamespace(id=1),
    )
    result = await run_update_role_description_slash_command(
        interaction,
        role=FakeRole(1),
        description="a" * 501,
        context={"is_blocked": lambda user: (False, None, None)},
    )
    assert result == SlashCommandResult(status="rejected", reason_code="description_too_long")


@pytest.mark.asyncio
async def test_role_info_helper_uses_snapshot(monkeypatch):
    role = FakeRole(10, name="관리자", color=discord.Color.blue())
    interaction = FakeInteraction(user=FakeUser(1), guild=SimpleNamespace(id=1))
    monkeypatch.setattr(
        handlers_module,
        "build_role_info_snapshot",
        lambda **kwargs: SimpleNamespace(
            role_name="관리자",
            role_mention="<@&10>",
            role_id=10,
            color_label=discord.Color.blue(),
            member_count=3,
            description="설명",
            enabled_permissions=("역할 관리하기",),
            member_mentions=("<@1>", "<@2>", "<@3>"),
            cannot_moderate_role_mentions=("<@&99>",),
        ),
    )

    result = await run_role_info_slash_command(
        interaction,
        role=role,
        context={"is_blocked": lambda user: (False, None, None), "permission_map": {}},
    )

    assert result == SlashCommandResult(status="completed", reason_code="role_info_checked")
    assert "역할 설명: 설명" in interaction.followup.sent[0]["embed"].description
    assert "멤버: <@1>, <@2>, <@3>" in interaction.followup.sent[0]["embed"].description


@pytest.mark.asyncio
async def test_invite_route_helpers_cover_update_known_unknown_and_join_route(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))
    update_mock = AsyncMock(return_value=SimpleNamespace(status="updated"))
    monkeypatch.setattr(handlers_module, "update_invite_route_memo_entry", update_mock)

    result = await run_set_invite_route_memo_slash_command(
        interaction,
        invite_code="abc",
        memo="메모",
        context={"is_blocked": lambda user: (False, None, None)},
    )
    assert result == SlashCommandResult(status="completed", reason_code="invite_route_memo_updated")

    unknown_interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))
    monkeypatch.setattr(
        handlers_module,
        "build_invite_route_report",
        AsyncMock(return_value=InviteRouteReport(status="unknown", entries=(InviteRouteEntry(invite_code=None, memo=None, rendered_label="*(알 수 없음)*"),))),
    )
    result = await run_check_invite_route_slash_command(
        unknown_interaction,
        target_user=FakeUser(20, mention="<@20>"),
        context={"is_blocked": lambda user: (False, None, None)},
    )
    assert result == SlashCommandResult(status="completed", reason_code="invite_route_unknown")

    join_route_interaction = FakeInteraction(user=FakeUser(99), guild=SimpleNamespace(id=1))
    monkeypatch.setattr(
        handlers_module,
        "update_user_join_route_entry",
        lambda **kwargs: SimpleNamespace(status="found", join_route=kwargs["join_route"]),
    )
    result = await run_set_user_join_route_slash_command(
        join_route_interaction,
        target_user=FakeUser(20, mention="<@20>"),
        join_route="트위터",
        context={"using_server": 1, "developer": 99},
    )
    assert result == SlashCommandResult(status="completed", reason_code="join_route_updated")


@pytest.mark.asyncio
async def test_check_user_join_route_helper_formats_missing_and_found(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(99), guild=SimpleNamespace(id=1))
    monkeypatch.setattr(handlers_module, "get_user_join_route_entry", lambda **kwargs: SimpleNamespace(status="missing", join_route=None))

    result = await run_check_user_join_route_slash_command(
        interaction,
        target_user=FakeUser(20, mention="<@20>"),
        context={"developer": 99},
    )

    assert result == SlashCommandResult(status="completed", reason_code="join_route_checked")
    assert "설정되지 않았습니다." in interaction.followup.sent[0]["embed"].description


@pytest.mark.asyncio
async def test_blockhistory_helpers_enforce_developer_gate(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))

    delete_result = await run_delete_blockhistory_entry_slash_command(
        interaction,
        entry_id=1,
        context={"developer": 999},
    )
    assert delete_result == SlashCommandResult(status="rejected", reason_code="missing_developer_permission")

    add_interaction = FakeInteraction(user=FakeUser(999), guild=SimpleNamespace(id=1))
    captured = {}
    monkeypatch.setattr(
        handlers_module,
        "add_blockhistory_entry",
        lambda **kwargs: captured.update(kwargs) or SimpleNamespace(status="added"),
    )
    add_result = await run_add_blockhistory_entry_slash_command(
        add_interaction,
        target_user=FakeUser(20),
        admin_user=FakeUser(30),
        reason_text="사유",
        type_label="warn",
        extra_value=2,
        context={"developer": 999},
    )
    assert add_result == SlashCommandResult(status="completed", reason_code="blockhistory_added")
    assert captured["user_id"] == 20
    assert add_interaction.followup.sent[0]["ephemeral"] is True


@pytest.mark.asyncio
async def test_developer_command_helper_covers_gate_and_known_branches(monkeypatch):
    non_dev_interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))
    result = await run_developer_command_slash_command(
        non_dev_interaction,
        command_id=1,
        input1=None,
        input2=None,
        input3=None,
        context={"developer": 999},
    )
    assert result == SlashCommandResult(status="rejected", reason_code="missing_developer_permission")

    dev_interaction = FakeInteraction(user=FakeUser(999), guild=SimpleNamespace(id=1))
    result = await run_developer_command_slash_command(
        dev_interaction,
        command_id=1,
        input1=None,
        input2=None,
        input3=None,
        context={"developer": 999},
    )
    assert result == SlashCommandResult(status="completed", reason_code="deprecated_command_1")

    save_interaction = FakeInteraction(user=FakeUser(999), guild=SimpleNamespace(id=1))
    captured = {}
    result = await run_developer_command_slash_command(
        save_interaction,
        command_id=15,
        input1="20",
        input2="invite-code",
        input3=None,
        context={
            "developer": 999,
            "save_invite_log": lambda user_id, invite_code, server_id: captured.update(
                {"user_id": user_id, "invite_code": invite_code, "server_id": server_id}
            ),
        },
    )
    assert result == SlashCommandResult(status="completed", reason_code="developer_command_15")
    assert captured == {"user_id": 20, "invite_code": "invite-code", "server_id": 1}


@pytest.mark.asyncio
async def test_backup_and_restore_helpers_cover_missing_and_success_paths(tmp_path, monkeypatch):
    async def fake_download_bytes(url):
        return b"data"

    class FakeResponseCtx:
        def __init__(self):
            self.status = 200

        async def read(self):
            return b"data"

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeClientSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, url):
            return FakeResponseCtx()

    monkeypatch.setattr(handlers_module.aiohttp, "ClientSession", FakeClientSession)

    backup_user = FakeUser(999)
    backup_channel = FakeHistoryChannel(
        [
            FakeMessage(10, "안녕", [FakeAttachment("a.png", "https://example.com/a.png")]),
            FakeMessage(20, "", []),
        ]
    )
    backup_interaction = FakeInteraction(user=backup_user, guild=SimpleNamespace(id=1, name="테스트"), channel=backup_channel)

    backup_result = await run_backup_channel_slash_command(
        backup_interaction,
        backup_name="backup-one",
        limit=2,
        context={"using_server": 1, "developer": 999, "backup_folder": str(tmp_path)},
    )

    assert backup_result == SlashCommandResult(status="completed", reason_code="channel_backup_completed")
    assert "`backup-one` 백업이 완료되었습니다." == backup_interaction.followup.sent[0]["content"]
    assert (tmp_path / "backup-one" / "messages.json").exists()

    restore_interaction = FakeInteraction(user=FakeUser(999), guild=SimpleNamespace(id=1), channel=FakeRestoreChannel())
    restore_result = await run_restore_channel_slash_command(
        restore_interaction,
        backup_name="missing",
        context={"using_server": 1, "developer": 999, "backup_folder": str(tmp_path), "bot": SimpleNamespace(fetch_user=AsyncMock())},
    )
    assert restore_result == SlashCommandResult(status="rejected", reason_code="backup_missing")

    fetch_user = AsyncMock(return_value=SimpleNamespace(display_name="양파", avatar=SimpleNamespace(url="https://example.com/avatar.png")))
    restore_interaction = FakeInteraction(user=FakeUser(999), guild=SimpleNamespace(id=1), channel=FakeRestoreChannel())
    restore_result = await run_restore_channel_slash_command(
        restore_interaction,
        backup_name="backup-one",
        context={"using_server": 1, "developer": 999, "backup_folder": str(tmp_path), "bot": SimpleNamespace(fetch_user=fetch_user)},
    )

    assert restore_result == SlashCommandResult(status="completed", reason_code="channel_restore_completed")
    webhook = restore_interaction.channel.webhooks[0]["webhook"]
    assert webhook.sent[0]["content"] == "안녕"
    assert restore_interaction.followup.sent[0]["content"] == "`backup-one` 복원이 완료되었습니다."


def test_main_uses_admin_support_helpers_instead_of_direct_wave3_bodies():
    source = Path("main.py").read_text(encoding="utf-8")
    assert "from bot_app.commands.slash_admin_support_handlers import (" in source
    assert "await run_developer_command_slash_command(" in source
    assert "await run_resolve_post_slash_command(" in source
    assert "await run_update_role_description_slash_command(" in source
    assert "await run_role_info_slash_command(" in source
    assert "await run_set_invite_route_memo_slash_command(" in source
    assert "await run_check_invite_route_slash_command(" in source
    assert "await run_delete_blockhistory_entry_slash_command(" in source
    assert "await run_add_blockhistory_entry_slash_command(" in source
    assert '@bot.tree.command(name = "구분역할설정"' not in source
    assert '@bot.tree.command(name="채널백업"' not in source
