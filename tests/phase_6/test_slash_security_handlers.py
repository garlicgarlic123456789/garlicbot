import ast
import copy
import warnings
from pathlib import Path
from types import SimpleNamespace

import discord
import pytest

import bot_app.commands.slash_security_handlers as handlers_module
from bot_app.commands.slash_security_handlers import (
    run_anti_nuke_setting_slash_command,
    run_anti_nuke_whitelist_slash_command,
    run_automod_setup_slash_command,
    run_automod_exception_channel_slash_command,
    run_bulk_delete_slash_command,
    run_check_restriction_slash_command,
    run_channel_command_permission_slash_command,
    run_delete_invites_slash_command,
    run_quarantine_user_slash_command,
    run_restrict_user_slash_command,
    run_security_action_slash_command,
    run_server_command_permission_slash_command,
    run_set_quarantine_role_slash_command,
    run_unrestrict_user_slash_command,
)
from bot_app.types.readability_contracts import ErrorTrackedSlashCommandResult, SlashCommandResult


class FakePermissions:
    def __init__(self, **kwargs):
        self.moderate_members = kwargs.get("moderate_members", False)
        self.manage_channels = kwargs.get("manage_channels", False)
        self.manage_roles = kwargs.get("manage_roles", False)
        self.administrator = kwargs.get("administrator", False)


class FakeRole:
    def __init__(self, role_id: int, *, mention: str | None = None):
        self.id = role_id
        self.mention = mention or f"<@&{role_id}>"


class FakeUser:
    def __init__(self, user_id: int, *, top_role=1, permissions=None, display_name="관리자"):
        self.id = user_id
        self.mention = f"<@{user_id}>"
        self.top_role = top_role
        self.guild_permissions = permissions or FakePermissions()
        self.display_name = display_name


class FakeMember(FakeUser):
    def __init__(self, user_id: int, *, roles, top_role=1, permissions=None, display_name="대상"):
        super().__init__(user_id, top_role=top_role, permissions=permissions, display_name=display_name)
        self.roles = list(roles)
        self.removed_roles = []
        self.added_roles = []

    async def remove_roles(self, role, *, reason=None):
        self.removed_roles.append({"role": role, "reason": reason})

    async def add_roles(self, role, *, reason=None):
        self.added_roles.append({"role": role, "reason": reason})


class FakeResponse:
    def __init__(self):
        self.deferred = []
        self.sent = []

    async def defer(self, *, ephemeral=False, thinking=False):
        self.deferred.append({"ephemeral": ephemeral, "thinking": thinking})

    async def send_message(self, content=None, *, embed=None, ephemeral=False):
        self.sent.append({"content": content, "embed": embed, "ephemeral": ephemeral})


class FakeFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, content=None, *, embed=None, ephemeral=False):
        self.sent.append({"content": content, "embed": embed, "ephemeral": ephemeral})


class FakeChannelMessage:
    def __init__(self, message_id: int, author, content: str):
        self.id = message_id
        self.author = author
        self.content = content


class FakeDeleteChannel:
    def __init__(self, messages):
        self.id = 555
        self._messages = list(messages)
        self.deleted_batches = []

    async def fetch_message(self, message_id: int):
        for message in self._messages:
            if message.id == message_id:
                return message
        raise discord.NotFound(response=SimpleNamespace(status=404, reason="not found"), message="missing")

    async def history(self, *, limit=None, after=None, before=None):
        for message in self._messages:
            if after is not None and message.id <= after.id:
                continue
            if before is not None and message.id >= before.id:
                continue
            yield message

    async def delete_messages(self, messages, *, reason=None):
        self.deleted_batches.append(
            {
                "message_ids": [message.id for message in messages],
                "reason": reason,
            }
        )


class FakeInvite:
    def __init__(self, inviter_id: int):
        self.inviter = SimpleNamespace(id=inviter_id)
        self.deleted = False

    async def delete(self):
        self.deleted = True


class FakeGuild:
    def __init__(self, guild_id: int, *, owner_id=10, members=None, roles=None):
        self.id = guild_id
        self.owner_id = owner_id
        self.owner = SimpleNamespace(id=owner_id)
        self._members = members or {}
        self._roles = roles or {}
        self.edit_calls = []
        self._invites = []

    def get_member(self, user_id: int):
        return self._members.get(user_id)

    def get_role(self, role_id: int):
        return self._roles.get(role_id)

    async def edit(self, **kwargs):
        self.edit_calls.append(kwargs)

    async def invites(self):
        return list(self._invites)


class FakeBot:
    def __init__(self):
        self.channels = {}

    def get_channel(self, channel_id: int):
        return self.channels.get(channel_id)


class FakeLogChannel:
    def __init__(self):
        self.sent_embeds = []

    async def send(self, content=None, *, embed=None):
        self.sent_embeds.append(embed)


class FakeInteraction:
    def __init__(self, *, user, guild, channel=None):
        self.user = user
        self.guild = guild
        self.channel = channel
        self.response = FakeResponse()
        self.followup = FakeFollowup()


def _extract_main_wrapper(function_name: str):
    source = Path("main.py").read_text(encoding="utf-8")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        module_ast = ast.parse(source)
    function_node = next(node for node in module_ast.body if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name)
    function_copy = copy.deepcopy(function_node)
    function_copy.decorator_list = []
    wrapper_module = ast.Module(body=[function_copy], type_ignores=[])
    ast.fix_missing_locations(wrapper_module)
    return wrapper_module


@pytest.mark.asyncio
async def test_bulk_delete_helper_deletes_messages_and_sends_log(monkeypatch):
    actor = FakeUser(10, permissions=FakePermissions(manage_channels=True))
    target_user = FakeUser(20)
    messages = [
        FakeChannelMessage(100, actor, "시작"),
        FakeChannelMessage(101, target_user, "하나"),
        FakeChannelMessage(102, FakeUser(30), "둘"),
        FakeChannelMessage(103, target_user, "셋"),
    ]
    channel = FakeDeleteChannel(messages)
    guild = FakeGuild(1)
    interaction = FakeInteraction(user=actor, guild=guild, channel=channel)
    bot = FakeBot()
    log_channel = FakeLogChannel()
    bot.channels[700] = log_channel

    result = await run_bulk_delete_slash_command(
        interaction,
        start_message_link="https://discord.com/channels/1/555/100",
        end_message_link=None,
        target_user=target_user,
        reason_text="정리",
        context={"bot": bot, "is_blocked": lambda user: (False, None, None), "get_log_channel": lambda guild_id: {"editdelete": 700}},
    )

    assert result == SlashCommandResult(status="completed", reason_code="bulk_delete_completed")
    assert interaction.response.deferred == [{"ephemeral": True, "thinking": False}]
    assert channel.deleted_batches == [
        {"message_ids": [101, 103], "reason": "사용자 10의 명령어 사용. 사유: 정리"}
    ]
    assert interaction.followup.sent[0]["content"] == "**[알림]** 2개의 메시지가 삭제되었습니다."
    assert log_channel.sent_embeds[0].title == "메시지 일괄 삭제"
    assert log_channel.sent_embeds[1].title == "메시지 일괄 삭제 로그"


@pytest.mark.asyncio
async def test_security_action_helper_validates_duration_and_calls_service(monkeypatch):
    actor = FakeUser(10, permissions=FakePermissions(moderate_members=True))
    guild = FakeGuild(1)
    interaction = FakeInteraction(user=actor, guild=guild, channel=None)
    captured = {}

    async def fake_apply_guild_security_action(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(handlers_module, "apply_guild_security_action", fake_apply_guild_security_action)

    result = await run_security_action_slash_command(
        interaction,
        server_join_block_text="10분",
        dm_block_text="30초",
        reason_text="점검",
    )

    assert result == SlashCommandResult(status="completed", reason_code="security_action_completed")
    assert captured["actor"] is actor
    assert captured["server_join_block_seconds"] == 600
    assert captured["dm_block_seconds"] == 30
    assert captured["reason_text"] == "점검"
    assert interaction.followup.sent[0]["embed"].description == "처리되었습니다."


@pytest.mark.asyncio
async def test_restrict_user_helper_requires_developer_and_persists(monkeypatch):
    actor = FakeUser(10)
    interaction = FakeInteraction(user=actor, guild=FakeGuild(1))
    target_user = FakeUser(20)
    captured = {}

    monkeypatch.setattr(
        handlers_module,
        "add_developer_restriction",
        lambda **kwargs: captured.update(kwargs),
    )

    result = await run_restrict_user_slash_command(
        interaction,
        target_user=target_user,
        reason_text="도배",
        until_date_label="2099-01-01",
        context={"developer": 10},
    )

    assert result == SlashCommandResult(status="completed", reason_code="restriction_added")
    assert captured == {"user_id": 20, "reason_text": "도배", "until_date_label": "2099-01-01"}
    assert interaction.followup.sent[0]["content"] == "20님을 2099-01-01까지 `도배`로 인해 이용제한 처리했습니다."


@pytest.mark.asyncio
async def test_unrestrict_user_helper_removes_stale_record_when_delete_succeeds(monkeypatch):
    actor = FakeUser(10)
    interaction = FakeInteraction(user=actor, guild=FakeGuild(1))
    target_user = FakeUser(20)

    monkeypatch.setattr(
        handlers_module,
        "remove_developer_restriction",
        lambda **kwargs: SimpleNamespace(status="removed", user_id=kwargs["user_id"]),
    )

    result = await run_unrestrict_user_slash_command(
        interaction,
        target_user=target_user,
        context={"developer": 10},
    )

    assert result == SlashCommandResult(status="completed", reason_code="restriction_removed")
    assert interaction.followup.sent[0]["content"] == "20님의 이용제한을 해제했습니다."


@pytest.mark.asyncio
async def test_unrestrict_user_helper_rejects_when_no_record_exists(monkeypatch):
    actor = FakeUser(10)
    interaction = FakeInteraction(user=actor, guild=FakeGuild(1))
    target_user = FakeUser(20)

    monkeypatch.setattr(
        handlers_module,
        "remove_developer_restriction",
        lambda **kwargs: SimpleNamespace(status="missing", user_id=kwargs["user_id"]),
    )

    result = await run_unrestrict_user_slash_command(
        interaction,
        target_user=target_user,
        context={"developer": 10},
    )

    assert result == SlashCommandResult(status="rejected", reason_code="restriction_not_found")
    assert interaction.followup.sent[0]["content"] == "20님은 차단되어 있지 않습니다."


@pytest.mark.asyncio
async def test_channel_permission_helper_requires_target_and_calls_service(monkeypatch):
    actor = FakeUser(10, permissions=FakePermissions(manage_channels=True, manage_roles=True))
    interaction = FakeInteraction(user=actor, guild=FakeGuild(1))
    channel = SimpleNamespace(id=30)
    role = FakeRole(40)
    captured = {}

    monkeypatch.setattr(handlers_module, "update_channel_command_permission", lambda **kwargs: captured.update(kwargs))

    result = await run_channel_command_permission_slash_command(
        interaction,
        command_name="마늘아",
        channel=channel,
        permission="allow",
        role=role,
        user=None,
    )

    assert result == SlashCommandResult(status="completed", reason_code="channel_permission_updated")
    assert captured == {
        "server_id": 1,
        "command_name": "마늘아",
        "channel_id": 30,
        "permission": "allow",
        "role_id": 40,
        "user_id": None,
    }


@pytest.mark.asyncio
async def test_delete_invites_helper_deletes_matching_invites(monkeypatch):
    actor = FakeUser(10)
    target_user = FakeUser(20)
    guild = FakeGuild(1)
    invite_a = FakeInvite(inviter_id=20)
    invite_b = FakeInvite(inviter_id=30)
    invite_c = FakeInvite(inviter_id=20)
    guild._invites = [invite_a, invite_b, invite_c]
    interaction = FakeInteraction(user=actor, guild=guild)

    result = await run_delete_invites_slash_command(
        interaction,
        target_user=target_user,
    )

    assert result == SlashCommandResult(status="completed", reason_code="invite_delete_completed")
    assert invite_a.deleted is True
    assert invite_b.deleted is False
    assert invite_c.deleted is True
    assert interaction.followup.sent[0]["content"] == "20가 만든 초대 링크 2개를 삭제했습니다."


@pytest.mark.asyncio
async def test_check_restriction_helper_reports_blocked_state(monkeypatch):
    actor = FakeUser(10)
    target_user = FakeUser(20)
    interaction = FakeInteraction(user=actor, guild=FakeGuild(1))

    monkeypatch.setattr(
        handlers_module,
        "get_developer_restriction_state",
        lambda **kwargs: SimpleNamespace(status="blocked", reason="도배", blocked_until_label="2099-01-01"),
    )

    result = await run_check_restriction_slash_command(
        interaction,
        target_user=target_user,
    )

    assert result == SlashCommandResult(status="completed", reason_code="restriction_checked_blocked")
    assert interaction.followup.sent[0]["content"] == "20님은 `도배` 사유로 2099-01-01까지 이용 제한 중입니다."


@pytest.mark.asyncio
async def test_server_permission_helper_requires_role_management_and_calls_service(monkeypatch):
    actor = FakeUser(10, permissions=FakePermissions(manage_channels=True, manage_roles=True))
    interaction = FakeInteraction(user=actor, guild=FakeGuild(1))
    role = FakeRole(41)
    captured = {}

    monkeypatch.setattr(handlers_module, "update_server_command_permission", lambda **kwargs: captured.update(kwargs))

    result = await run_server_command_permission_slash_command(
        interaction,
        command_name="마느라",
        permission="limit",
        role=role,
    )

    assert result == SlashCommandResult(status="completed", reason_code="server_permission_updated")
    assert captured == {
        "server_id": 1,
        "command_name": "마느라",
        "permission": "limit",
        "role_id": 41,
    }
    assert interaction.followup.sent[0]["embed"].description == "서버별 명령어 권한이 설정되었습니다."


@pytest.mark.asyncio
async def test_automod_exception_helper_updates_channel_setting(monkeypatch):
    actor = FakeUser(10, permissions=FakePermissions(administrator=True))
    interaction = FakeInteraction(user=actor, guild=FakeGuild(1))
    channel = SimpleNamespace(id=123, mention="<#123>")
    captured = {}

    monkeypatch.setattr(
        handlers_module,
        "update_automod_exception_channel_setting",
        lambda **kwargs: captured.update(kwargs),
    )

    result = await run_automod_exception_channel_slash_command(
        interaction,
        channel=channel,
        enabled=True,
        context={"is_blocked": lambda user: (False, None, None)},
    )

    assert result == SlashCommandResult(status="completed", reason_code="automod_exception_updated")
    assert captured == {"server_id": 1, "channel_id": 123, "enabled": True}
    assert interaction.followup.sent[0]["embed"].description == "채널 <#123>의 자동 검열 예외 설정이 완료되었습니다."


@pytest.mark.asyncio
async def test_automod_setup_helper_rejects_restricted_server(monkeypatch):
    actor = FakeUser(10, permissions=FakePermissions(administrator=True))
    interaction = FakeInteraction(user=actor, guild=FakeGuild(2))

    result = await run_automod_setup_slash_command(
        interaction,
        political_enabled=True,
        sexual_enabled=False,
        invite_enabled=False,
        mention_enabled=False,
        whitelist_permission="admin",
        political_timeout_seconds=10,
        sexual_timeout_seconds=0,
        invite_timeout_seconds=0,
        mention_timeout_seconds=0,
        context={"is_blocked": lambda user: (False, None, None), "using_server": 1, "developer": 999},
    )

    assert result == SlashCommandResult(status="rejected", reason_code="automod_restricted_server")
    assert "정치 발언 및 성적인 발언 검열 기능은 아직 여러 서버들에서 지원되지 않습니다." in interaction.followup.sent[0]["embed"].description


@pytest.mark.asyncio
async def test_set_quarantine_role_helper_tracks_error_count(monkeypatch):
    actor = FakeUser(10, permissions=FakePermissions(manage_roles=True))
    interaction = FakeInteraction(user=actor, guild=FakeGuild(1))
    captured = {}

    monkeypatch.setattr(handlers_module, "update_quarantine_role_setting", lambda **kwargs: captured.update(kwargs))

    result = await run_set_quarantine_role_slash_command(
        interaction,
        quarantine_role=FakeRole(55),
        context={"is_blocked": lambda user: (False, None, None)},
        error_count=3,
    )

    assert result == ErrorTrackedSlashCommandResult(status="completed", error_count=3, reason_code="quarantine_role_updated")
    assert captured == {"server_id": 1, "role_id": 55}


@pytest.mark.asyncio
async def test_quarantine_user_helper_removes_roles_and_adds_quarantine_role(monkeypatch):
    admin_role = FakeRole(999)
    target_role = FakeRole(111)
    quarantine_role = FakeRole(222)
    actor = FakeMember(10, roles=[FakeRole(0), admin_role], top_role=10, display_name="운영자")
    target_member = FakeMember(20, roles=[FakeRole(0), target_role], top_role=1)
    guild = FakeGuild(1, members={10: actor, 20: target_member}, roles={222: quarantine_role})
    interaction = FakeInteraction(user=actor, guild=guild)

    monkeypatch.setattr(handlers_module, "get_quarantine_role_id", lambda **kwargs: 222)

    result = await run_quarantine_user_slash_command(
        interaction,
        target_user=SimpleNamespace(id=20, mention="<@20>", top_role=1),
        context={"is_blocked": lambda user: (False, None, None), "using_server": 1, "admin_role_id": 999},
        error_count=4,
    )

    assert result == ErrorTrackedSlashCommandResult(status="completed", error_count=4, reason_code="quarantine_applied")
    assert target_member.removed_roles[0]["role"] is target_role
    assert target_member.added_roles[0]["role"] is quarantine_role


@pytest.mark.asyncio
async def test_anti_nuke_setting_and_whitelist_helpers_call_services(monkeypatch):
    actor = FakeUser(10)
    guild = FakeGuild(1, owner_id=10)
    interaction = FakeInteraction(user=actor, guild=guild)
    captured = []

    monkeypatch.setattr(handlers_module, "update_anti_nuke_setting", lambda **kwargs: captured.append(("setting", kwargs)))
    monkeypatch.setattr(handlers_module, "update_anti_nuke_whitelist_setting", lambda **kwargs: captured.append(("whitelist", kwargs)))

    setting_result = await run_anti_nuke_setting_slash_command(
        interaction,
        enabled_label="활성화",
        log_channel=SimpleNamespace(id=300),
        error_count=5,
    )
    whitelist_result = await run_anti_nuke_whitelist_slash_command(
        interaction,
        target_user=FakeUser(30),
        enabled_label="비활성화",
        error_count=5,
    )

    assert setting_result == ErrorTrackedSlashCommandResult(status="completed", error_count=5, reason_code="anti_nuke_updated")
    assert whitelist_result == ErrorTrackedSlashCommandResult(status="completed", error_count=5, reason_code="anti_nuke_whitelist_updated")
    assert captured == [
        ("setting", {"server_id": 1, "enabled": True, "log_channel_id": 300}),
        ("whitelist", {"server_id": 1, "user_id": 30, "enabled": False}),
    ]


@pytest.mark.asyncio
async def test_main_wave5_wrappers_delegate_to_security_helpers():
    source = Path("main.py").read_text(encoding="utf-8")
    wrapper_names = [
        "bulk_delete",
        "delete_invites",
        "보안조치",
        "제한",
        "제한해제",
        "차단확인",
        "channel_command_perm_setting",
        "server_command_perm_setting",
        "automod_exception_channel_setup",
        "automod_setup",
        "격리역할설정",
        "격리",
        "anti_nuke_settings",
        "anti_nuke_whitelist_settings",
    ]

    wrappers = {name: _extract_main_wrapper(name) for name in wrapper_names}
    captured = {}

    async def fake_helper(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SimpleNamespace(error_count=77)

    namespace = {
        "discord": SimpleNamespace(
            Interaction=object,
            User=object,
            Member=object,
            Role=object,
            TextChannel=object,
            abc=SimpleNamespace(GuildChannel=object),
        ),
        "run_bulk_delete_slash_command": fake_helper,
        "run_delete_invites_slash_command": fake_helper,
        "run_security_action_slash_command": fake_helper,
        "run_restrict_user_slash_command": fake_helper,
        "run_unrestrict_user_slash_command": fake_helper,
        "run_check_restriction_slash_command": fake_helper,
        "run_channel_command_permission_slash_command": fake_helper,
        "run_server_command_permission_slash_command": fake_helper,
        "run_automod_exception_channel_slash_command": fake_helper,
        "run_automod_setup_slash_command": fake_helper,
        "run_set_quarantine_role_slash_command": fake_helper,
        "run_quarantine_user_slash_command": fake_helper,
        "run_anti_nuke_setting_slash_command": fake_helper,
        "run_anti_nuke_whitelist_slash_command": fake_helper,
        "bot": object(),
        "is_blocked": object(),
        "get_log_channel": object(),
        "developer": 999,
        "using_server": 1,
        "admin_id": 123,
        "error": 9,
    }

    for name, wrapper_module in wrappers.items():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            exec(compile(wrapper_module, "main.py", "exec"), namespace)

    interaction = FakeInteraction(user=FakeUser(10), guild=FakeGuild(1))
    await namespace["bulk_delete"](interaction, "start", None, None, "사유")
    assert captured["kwargs"]["start_message_link"] == "start"
    await namespace["delete_invites"](interaction, FakeUser(20))
    assert captured["kwargs"]["target_user"].id == 20
    await namespace["보안조치"](interaction, "10분", "20초", "사유")
    assert captured["kwargs"]["server_join_block_text"] == "10분"
    await namespace["제한"](interaction, FakeUser(20), "사유", "2099-01-01")
    assert captured["kwargs"]["context"]["developer"] == 999
    await namespace["제한해제"](interaction, FakeUser(20))
    assert captured["kwargs"]["target_user"].id == 20
    await namespace["차단확인"](interaction, FakeUser(20))
    assert captured["kwargs"]["target_user"].id == 20
    await namespace["channel_command_perm_setting"](interaction, "마늘아", SimpleNamespace(id=30), "allow", FakeRole(40), None)
    assert captured["kwargs"]["command_name"] == "마늘아"
    await namespace["server_command_perm_setting"](interaction, "마늘아", "allow", FakeRole(41))
    assert captured["kwargs"]["role"].id == 41
    await namespace["automod_exception_channel_setup"](interaction, SimpleNamespace(id=50, mention="<#50>"), True)
    assert captured["kwargs"]["enabled"] is True
    await namespace["automod_setup"](interaction, True, False, False, False, "admin", 1, 2, 3, 4)
    assert captured["kwargs"]["political_enabled"] is True
    await namespace["격리역할설정"](interaction, FakeRole(60))
    assert namespace["error"] == 77
    await namespace["격리"](interaction, SimpleNamespace(id=20, mention="<@20>"))
    assert namespace["error"] == 77
    await namespace["anti_nuke_settings"](interaction, "활성화", SimpleNamespace(id=70))
    assert namespace["error"] == 77
    await namespace["anti_nuke_whitelist_settings"](interaction, FakeUser(30), "비활성화")
    assert namespace["error"] == 77

    assert "run_bulk_delete_slash_command(" in source
    assert "run_delete_invites_slash_command(" in source
    assert "run_security_action_slash_command(" in source
    assert "run_restrict_user_slash_command(" in source
    assert "run_unrestrict_user_slash_command(" in source
    assert "run_check_restriction_slash_command(" in source
    assert "run_channel_command_permission_slash_command(" in source
    assert "run_server_command_permission_slash_command(" in source
    assert "run_automod_exception_channel_slash_command(" in source
    assert "run_automod_setup_slash_command(" in source
    assert "run_set_quarantine_role_slash_command(" in source
    assert "run_quarantine_user_slash_command(" in source
    assert "run_anti_nuke_setting_slash_command(" in source
    assert "run_anti_nuke_whitelist_slash_command(" in source
