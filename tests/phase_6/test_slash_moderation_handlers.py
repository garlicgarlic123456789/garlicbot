import ast
import copy
import warnings
from pathlib import Path
from types import SimpleNamespace

import discord
import pytest

import bot_app.commands.slash_moderation_handlers as handlers_module
from bot_app.commands.slash_moderation_handlers import (
    run_bulk_ban_slash_command,
    run_bulk_unban_slash_command,
    run_ban_slash_command,
    run_kick_slash_command,
    run_unban_slash_command,
)
from bot_app.services.moderation_service import record_ban_action, record_kick_action, record_unban_action
from bot_app.types.readability_contracts import ErrorTrackedSlashCommandResult, SlashCommandResult
from tests.helpers.fakes import FakeBot, FakeTextChannel


class FakePermissions:
    def __init__(self, *, ban_members=False, kick_members=False, moderate_members=False, manage_guild=False):
        self.ban_members = ban_members
        self.kick_members = kick_members
        self.moderate_members = moderate_members
        self.manage_guild = manage_guild


class FakeAuthor:
    def __init__(self, author_id: int, *, top_role=10):
        self.id = author_id
        self.bot = False
        self.mention = f"<@{author_id}>"
        self.top_role = top_role
        self.guild_permissions = FakePermissions(ban_members=True, kick_members=True)


class FakeTargetUser:
    def __init__(self, user_id: int, *, top_role=1):
        self.id = user_id
        self.mention = f"<@{user_id}>"
        self.top_role = top_role


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


class FakeInteraction:
    def __init__(self, *, user, guild):
        self.user = user
        self.guild = guild
        self.response = FakeResponse()
        self.followup = FakeFollowup()


class FakeGuild:
    def __init__(self, guild_id: int, *, owner_id: int = 500, fetched_member=None):
        self.id = guild_id
        self.owner_id = owner_id
        self._fetched_member = fetched_member
        self.kick_calls = []
        self.ban_calls = []
        self.unban_calls = []

    async def kick(self, member, *, reason=None):
        self.kick_calls.append({"member": member, "reason": reason})

    async def ban(self, user, *, reason=None, delete_message_seconds=0):
        self.ban_calls.append({"user": user, "reason": reason, "delete_message_seconds": delete_message_seconds})

    async def unban(self, user, *, reason=None):
        self.unban_calls.append({"user": user, "reason": reason})

    async def fetch_member(self, member_id):
        if isinstance(self._fetched_member, Exception):
            raise self._fetched_member
        return self._fetched_member


class FakeModerationRepository:
    def __init__(self):
        self.calls = []

    def add_blockhistory(self, user_id: int, admin_id: int, reason: str, type_: str, addinfo: int, server_id: int):
        self.calls.append((user_id, admin_id, reason, type_, addinfo, server_id))


def _extract_main_wrapper(function_name: str):
    source = Path("main.py").read_text(encoding="utf-8")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        module_ast = ast.parse(source)
    function_node = next(
        node for node in module_ast.body if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name
    )
    function_copy = copy.deepcopy(function_node)
    function_copy.decorator_list = []
    wrapper_module = ast.Module(body=[function_copy], type_ignores=[])
    ast.fix_missing_locations(wrapper_module)
    return wrapper_module


@pytest.mark.asyncio
async def test_record_kick_ban_and_unban_actions_write_named_history_entries():
    repository = FakeModerationRepository()

    kick_result = record_kick_action(server_id=1, user_id=2, admin_id=3, reason=None, repository=repository)
    ban_result = record_ban_action(server_id=1, user_id=2, admin_id=3, reason="사유", repository=repository)
    unban_result = record_unban_action(server_id=1, user_id=2, admin_id=3, reason=None, repository=repository)

    assert kick_result.action_type == "kick"
    assert kick_result.reason == "*(사유 입력되지 않음)*"
    assert ban_result.action_type == "ban"
    assert ban_result.reason == "사유"
    assert unban_result.action_type == "unban"
    assert unban_result.reason == "*(사유 입력되지 않음)*"
    assert repository.calls == [
        (2, 3, "*(사유 입력되지 않음)*", "kick", 0, 1),
        (2, 3, "사유", "ban", 0, 1),
        (2, 3, "*(사유 입력되지 않음)*", "unban", 0, 1),
    ]


@pytest.mark.asyncio
async def test_kick_helper_executes_service_logging_and_anti_nuke(monkeypatch):
    bot = FakeBot()
    record_channel = FakeTextChannel(channel_id=100)
    message_log_channel = FakeTextChannel(channel_id=101)
    bot.channels[100] = record_channel
    bot.channels[101] = message_log_channel
    anti_nuke_calls = []
    service_calls = []

    def fake_record_kick_action(**kwargs):
        service_calls.append(kwargs)
        return SimpleNamespace(reason="추방 사유")

    async def fake_process_anti_nuke_ban(server_id, admin_id, guild):
        anti_nuke_calls.append((server_id, admin_id, guild.id))

    monkeypatch.setattr(handlers_module, "record_kick_action", fake_record_kick_action)
    guild = FakeGuild(1)
    target = FakeTargetUser(20, top_role=1)
    interaction = FakeInteraction(user=FakeAuthor(10, top_role=9), guild=guild)

    result = await run_kick_slash_command(
        interaction=interaction,
        target_user=target,
        reason_text="추방 사유",
        context={
            "friendly_list": [],
            "bot": bot,
            "using_server": 1,
            "record_channel": 100,
            "message_log": 101,
            "is_blocked": lambda user: (False, None, None),
            "process_anti_nuke_ban": fake_process_anti_nuke_ban,
        },
        error_count=4,
    )

    assert result == ErrorTrackedSlashCommandResult(status="completed", error_count=4, reason_code="kick_processed")
    assert guild.kick_calls == [{"member": target, "reason": "추방 사유"}]
    assert service_calls == [{"server_id": 1, "user_id": 20, "admin_id": 10, "reason": "추방 사유"}]
    assert record_channel.sent_embeds[0].title == "추방"
    assert message_log_channel.sent_embeds[0].title == "추방"
    assert interaction.followup.sent[0]["embed"].title == "추방"
    assert anti_nuke_calls == [(1, 10, 1)]


@pytest.mark.asyncio
async def test_ban_helper_handles_private_visibility_and_success(monkeypatch):
    bot = FakeBot()
    owner_notify_channel = FakeTextChannel(channel_id=200)
    message_log_channel = FakeTextChannel(channel_id=201)
    bot.channels[200] = owner_notify_channel
    bot.channels[201] = message_log_channel
    anti_nuke_calls = []
    service_calls = []

    rejected_interaction = FakeInteraction(user=FakeAuthor(10, top_role=9), guild=FakeGuild(1, owner_id=999))
    rejected_result = await run_ban_slash_command(
        interaction=rejected_interaction,
        target_user=FakeTargetUser(20),
        reason_text="사유",
        visibility="비공개",
        context={
            "friendly_list": [],
            "bot": bot,
            "using_server": 1,
            "owner_notify": 200,
            "message_log": 201,
            "is_blocked": lambda user: (False, None, None),
            "process_anti_nuke_ban": lambda *args: None,
        },
        error_count=2,
    )
    assert rejected_result == ErrorTrackedSlashCommandResult(
        status="rejected",
        error_count=2,
        reason_code="ban_private_visibility_denied",
    )

    def fake_record_ban_action(**kwargs):
        service_calls.append(kwargs)
        return SimpleNamespace(reason="밴 사유")

    async def fake_process_anti_nuke_ban(server_id, admin_id, guild):
        anti_nuke_calls.append((server_id, admin_id, guild.id))

    monkeypatch.setattr(handlers_module, "record_ban_action", fake_record_ban_action)
    target = FakeTargetUser(20)
    guild = FakeGuild(1, owner_id=10, fetched_member=FakeTargetUser(20, top_role=1))
    interaction = FakeInteraction(user=FakeAuthor(10, top_role=9), guild=guild)

    result = await run_ban_slash_command(
        interaction=interaction,
        target_user=target,
        reason_text="밴 사유",
        visibility="비공개",
        context={
            "friendly_list": [],
            "bot": bot,
            "using_server": 1,
            "owner_notify": 200,
            "message_log": 201,
            "is_blocked": lambda user: (False, None, None),
            "process_anti_nuke_ban": fake_process_anti_nuke_ban,
        },
        error_count=2,
    )

    assert result == ErrorTrackedSlashCommandResult(status="completed", error_count=2, reason_code="ban_processed")
    assert interaction.response.deferred == [{"ephemeral": True}]
    assert guild.ban_calls == [{"user": target, "reason": "밴 사유", "delete_message_seconds": 0}]
    assert service_calls == [{"server_id": 1, "user_id": 20, "admin_id": 10, "reason": "밴 사유"}]
    assert owner_notify_channel.sent_embeds[0].title == "차단"
    assert message_log_channel.sent_embeds[0].title == "차단"
    assert interaction.followup.sent[0]["embed"].title == "차단"
    assert anti_nuke_calls == [(1, 10, 1)]


@pytest.mark.asyncio
async def test_unban_helper_executes_public_log_flow(monkeypatch):
    bot = FakeBot()
    block_log_channel = FakeTextChannel(channel_id=300)
    message_log_channel = FakeTextChannel(channel_id=301)
    bot.channels[300] = block_log_channel
    bot.channels[301] = message_log_channel
    service_calls = []

    def fake_record_unban_action(**kwargs):
        service_calls.append(kwargs)
        return SimpleNamespace(reason="해제 사유")

    monkeypatch.setattr(handlers_module, "record_unban_action", fake_record_unban_action)
    monkeypatch.setattr(handlers_module, "get_block_log_channel_for_guild", lambda bot, guild_id: block_log_channel)

    guild = FakeGuild(1, owner_id=500)
    target = FakeTargetUser(25)
    interaction = FakeInteraction(user=FakeAuthor(10, top_role=9), guild=guild)

    result = await run_unban_slash_command(
        interaction=interaction,
        target_user=target,
        reason_text="해제 사유",
        visibility="공개",
        context={
            "bot": bot,
            "using_server": 1,
            "owner_notify": 999,
            "message_log": 301,
            "is_blocked": lambda user: (False, None, None),
        },
        error_count=8,
    )

    assert result == ErrorTrackedSlashCommandResult(status="completed", error_count=8, reason_code="unban_processed")
    assert guild.unban_calls == [{"user": target, "reason": "해제 사유"}]
    assert service_calls == [{"server_id": 1, "user_id": 25, "admin_id": 10, "reason": "해제 사유"}]
    assert block_log_channel.sent_embeds[0].title == "차단 해제"
    assert message_log_channel.sent_embeds[0].title == "차단 해제"
    assert interaction.followup.sent[0]["embed"].title == "차단 해제"


@pytest.mark.asyncio
async def test_bulk_ban_helper_records_success_and_failure_entries(monkeypatch):
    bot = FakeBot()
    block_log_channel = FakeTextChannel(channel_id=400)
    message_log_channel = FakeTextChannel(channel_id=401)
    bot.channels[400] = block_log_channel
    bot.channels[401] = message_log_channel

    recorded_calls = []

    async def fake_fetch_user(user_id: int):
        if user_id == 404:
            raise RuntimeError("missing user")
        return FakeTargetUser(user_id)

    def fake_record_ban_action(**kwargs):
        recorded_calls.append(kwargs)
        return SimpleNamespace(reason=kwargs["reason"] or "*(사유 입력되지 않음)*")

    monkeypatch.setattr(handlers_module, "get_block_log_channel_for_guild", lambda bot, guild_id: block_log_channel)
    monkeypatch.setattr(handlers_module, "record_ban_action", fake_record_ban_action)
    bot.fetch_user = fake_fetch_user

    guild = FakeGuild(1, owner_id=10)
    interaction = FakeInteraction(user=FakeAuthor(10, top_role=9), guild=guild)

    result = await run_bulk_ban_slash_command(
        interaction,
        user_ids_text="20, 404, 21",
        reason_text="벌크 사유",
        visibility="공개",
        context={
            "bot": bot,
            "using_server": 1,
            "owner_notify": 999,
            "message_log": 401,
            "is_blocked": lambda user: (False, None, None),
        },
    )

    assert result == SlashCommandResult(status="completed", reason_code="bulk_ban_processed")
    assert interaction.response.deferred == [{"ephemeral": False}]
    assert [call["reason"] for call in guild.ban_calls] == ["벌크 사유", "벌크 사유"]
    assert [call["delete_message_seconds"] for call in guild.ban_calls] == [0, 0]
    assert [call["user"].id for call in guild.ban_calls] == [20, 21]
    assert recorded_calls == [
        {"server_id": 1, "user_id": 20, "admin_id": 10, "reason": "벌크 사유"},
        {"server_id": 1, "user_id": 21, "admin_id": 10, "reason": "벌크 사유"},
    ]
    response_embed = interaction.followup.sent[0]["embed"]
    assert response_embed.title == "차단"
    assert response_embed.fields[0].value == "<@20>, <@21>"
    assert response_embed.fields[1].value == "<@404>"
    assert block_log_channel.sent_embeds[0].title == "차단"
    assert message_log_channel.sent_embeds[0].title == "차단"


@pytest.mark.asyncio
async def test_bulk_unban_helper_uses_private_visibility_owner_notify(monkeypatch):
    bot = FakeBot()
    owner_notify_channel = FakeTextChannel(channel_id=500)
    message_log_channel = FakeTextChannel(channel_id=501)
    bot.channels[500] = owner_notify_channel
    bot.channels[501] = message_log_channel

    recorded_calls = []

    async def fake_fetch_user(user_id: int):
        return FakeTargetUser(user_id)

    def fake_record_unban_action(**kwargs):
        recorded_calls.append(kwargs)
        return SimpleNamespace(reason=kwargs["reason"] or "*(사유 입력되지 않음)*")

    monkeypatch.setattr(handlers_module, "record_unban_action", fake_record_unban_action)
    bot.fetch_user = fake_fetch_user

    guild = FakeGuild(1, owner_id=10)
    interaction = FakeInteraction(user=FakeAuthor(10, top_role=9), guild=guild)

    result = await run_bulk_unban_slash_command(
        interaction,
        user_ids_text="30, 31",
        reason_text="None",
        visibility="비공개",
        context={
            "bot": bot,
            "using_server": 1,
            "owner_notify": 500,
            "message_log": 501,
            "is_blocked": lambda user: (False, None, None),
        },
    )

    assert result == SlashCommandResult(status="completed", reason_code="bulk_unban_processed")
    assert interaction.response.deferred == [{"ephemeral": True}]
    assert [call["user"].id for call in guild.unban_calls] == [30, 31]
    assert recorded_calls == [
        {"server_id": 1, "user_id": 30, "admin_id": 10, "reason": None},
        {"server_id": 1, "user_id": 31, "admin_id": 10, "reason": None},
    ]
    response_embed = interaction.followup.sent[0]["embed"]
    assert response_embed.title == "차단 해제"
    assert response_embed.fields[2].value == "*(사유 입력되지 않음)*"
    assert owner_notify_channel.sent_embeds[0].title == "차단 해제"
    assert message_log_channel.sent_embeds[0].title == "차단 해제"


@pytest.mark.asyncio
async def test_main_kick_ban_and_unban_wrappers_pass_expected_context():
    source = Path("main.py").read_text(encoding="utf-8")
    extracted_wrappers = {
        "kick": _extract_main_wrapper("kick"),
        "ban": _extract_main_wrapper("ban"),
        "unban": _extract_main_wrapper("unban"),
        "bulk_ban": _extract_main_wrapper("bulk_ban"),
        "bulk_unban": _extract_main_wrapper("bulk_unban"),
    }

    wrapper_specs = {
        "kick": {
            "helper_name": "run_kick_slash_command",
            "expected_context_keys": {"friendly_list", "bot", "using_server", "record_channel", "message_log", "is_blocked", "process_anti_nuke_ban"},
            "args": ("interaction", "사용자", "사유"),
        },
        "ban": {
            "helper_name": "run_ban_slash_command",
            "expected_context_keys": {"friendly_list", "bot", "using_server", "owner_notify", "message_log", "is_blocked", "process_anti_nuke_ban"},
            "args": ("interaction", "사용자", "사유", "제재내역공개여부"),
        },
        "unban": {
            "helper_name": "run_unban_slash_command",
            "expected_context_keys": {"bot", "using_server", "owner_notify", "message_log", "is_blocked"},
            "args": ("interaction", "사용자", "사유", "제재내역공개여부"),
        },
        "bulk_ban": {
            "helper_name": "run_bulk_ban_slash_command",
            "expected_context_keys": {"bot", "using_server", "owner_notify", "message_log", "is_blocked"},
            "args": ("interaction", "사용자_리스트", "사유", "제재내역공개여부"),
        },
        "bulk_unban": {
            "helper_name": "run_bulk_unban_slash_command",
            "expected_context_keys": {"bot", "using_server", "owner_notify", "message_log", "is_blocked"},
            "args": ("interaction", "사용자_리스트", "사유", "제재내역공개여부"),
        },
    }

    sentinels = {
        "friendly_list": object(),
        "bot": object(),
        "using_server": object(),
        "record_channel": object(),
        "owner_notify": object(),
        "message_log": object(),
        "is_blocked": object(),
        "process_anti_nuke_ban": object(),
        "error": 5,
    }

    for function_name, wrapper_module in extracted_wrappers.items():
        captured = {}

        async def fake_helper(interaction, *, context, target_user=None, reason_text=None, error_count=None, visibility=None, user_ids_text=None):
            captured.update(
                {
                    "interaction": interaction,
                    "target_user": target_user,
                    "reason_text": reason_text,
                    "context": context,
                    "error_count": error_count,
                    "visibility": visibility,
                    "user_ids_text": user_ids_text,
                }
            )
            return SimpleNamespace(error_count=99)

        namespace = {
            "discord": SimpleNamespace(Interaction=object, Member=object, User=object),
            "run_kick_slash_command": fake_helper,
            "run_ban_slash_command": fake_helper,
            "run_unban_slash_command": fake_helper,
            "run_bulk_ban_slash_command": fake_helper,
            "run_bulk_unban_slash_command": fake_helper,
            **sentinels,
        }
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            exec(compile(wrapper_module, "main.py", "exec"), namespace)

        interaction = FakeInteraction(user=FakeAuthor(10), guild=FakeGuild(1))
        target_user = FakeTargetUser(20)
        if function_name == "kick":
            await namespace[function_name](interaction, target_user, "사유")
        elif function_name in {"bulk_ban", "bulk_unban"}:
            await namespace[function_name](interaction, "20, 21", "사유", "비공개")
        else:
            await namespace[function_name](interaction, target_user, "사유", "비공개")

        assert captured["interaction"] is interaction
        if function_name in {"bulk_ban", "bulk_unban"}:
            assert captured["user_ids_text"] == "20, 21"
        else:
            assert captured["target_user"] is target_user
            assert captured["reason_text"] == "사유"
        if function_name != "kick":
            assert captured["visibility"] == "비공개"
        assert set(captured["context"]) == wrapper_specs[function_name]["expected_context_keys"]
        for key in wrapper_specs[function_name]["expected_context_keys"]:
            assert captured["context"][key] is sentinels[key]
        if function_name in {"kick", "ban", "unban"}:
            assert captured["error_count"] == 5
            assert namespace["error"] == 99

    assert "run_kick_slash_command(" in source
    assert "run_ban_slash_command(" in source
    assert "run_unban_slash_command(" in source
    assert "run_bulk_ban_slash_command(" in source
    assert "run_bulk_unban_slash_command(" in source
