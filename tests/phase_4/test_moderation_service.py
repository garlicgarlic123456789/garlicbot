from importlib import import_module
from pathlib import Path

import pytest

import bot_app.commands.slash_moderation_handlers as slash_moderation_handlers_module
from bot_app.events import message_handlers as message_handlers_module
from bot_app.events.message_handlers import handle_moderation_text_commands
from bot_app.commands.slash_moderation_handlers import (
    run_check_warning_slash_command,
    run_remove_timeout_slash_command,
    run_set_warn_limit_slash_command,
    run_timeout_slash_command,
    run_unwarn_slash_command,
    run_warn_slash_command,
)
from bot_app.repositories.moderation_repository import ModerationRepository
from bot_app.services.moderation_service import (
    DEFAULT_REASON,
    add_warning_action,
    finalize_warn_limit_ban,
    get_warning_status,
    parse_timeout_duration,
    record_timeout_action,
    record_untimeout_action,
    remove_warning_action,
    set_warn_limit,
)
from bot_app.types.readability_contracts import (
    ErrorTrackedSlashCommandResult,
    ModerationCommandResult,
    SlashCommandResult,
    UserBlockState,
    WarnLimitSettingResult,
    WarningStatusSnapshot,
)
from tests.helpers.fakes import FakeBot, FakeTextChannel


class FakePermissions:
    def __init__(self, *, ban_members=False, moderate_members=False, manage_guild=False):
        self.ban_members = ban_members
        self.moderate_members = moderate_members
        self.manage_guild = manage_guild


class FakeAuthor:
    def __init__(self, author_id: int, *, ban_members=False, moderate_members=False, manage_guild=False, top_role=10):
        self.id = author_id
        self.bot = False
        self.mention = f"<@{author_id}>"
        self.guild_permissions = FakePermissions(
            ban_members=ban_members,
            moderate_members=moderate_members,
            manage_guild=manage_guild,
        )
        self.top_role = top_role


class FakeMember:
    def __init__(self, member_id: int, *, top_role=1):
        self.id = member_id
        self.top_role = top_role
        self.mention = f"<@{member_id}>"
        self.edit_calls = []

    async def edit(self, **kwargs):
        self.edit_calls.append(kwargs)


class FakeGuild:
    def __init__(self, guild_id: int, *, owner_id: int = 999, member=None):
        self.id = guild_id
        self.owner_id = owner_id
        self._member = member
        self.ban_calls = []

    def get_member(self, member_id):
        return self._member

    async def ban(self, member, *, reason=None, delete_message_days=0):
        self.ban_calls.append(
            {
                "member": member,
                "reason": reason,
                "delete_message_days": delete_message_days,
            }
        )


class FakeMessage:
    def __init__(self, *, content: str, author, guild, channel):
        self.content = content
        self.author = author
        self.guild = guild
        self.channel = channel
        self.role_mentions = []
        self.message_snapshots = []
        self.replies = []

    async def reply(self, content=None, *, embed=None, mention_author=False):
        self.replies.append({"content": content, "embed": embed, "mention_author": mention_author})


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


class FakeSlashInteraction:
    def __init__(self, *, user, guild):
        self.user = user
        self.guild = guild
        self.response = FakeResponse()
        self.followup = FakeFollowup()


class FakeModerationRepository:
    def __init__(self, *, warn_max=None, add_warning_result=(0, 1, 1), remove_warning_result=(3, 1, 2)):
        self.warn_max = warn_max
        self.add_warning_result = add_warning_result
        self.remove_warning_result = remove_warning_result
        self.calls = []

    def get_warn_max(self, server_id: int):
        self.calls.append(("get_warn_max", server_id))
        return self.warn_max

    async def add_warning(self, server_id: int, user_id: int, amount: int):
        self.calls.append(("add_warning", server_id, user_id, amount))
        return self.add_warning_result

    async def remove_warning(self, server_id: int, user_id: int, amount: int):
        self.calls.append(("remove_warning", server_id, user_id, amount))
        return self.remove_warning_result

    async def reset_warning(self, server_id: int, user_id: int):
        self.calls.append(("reset_warning", server_id, user_id))

    def add_blockhistory(self, user_id: int, admin_id: int, reason: str, type_: str, addinfo: int, server_id: int):
        self.calls.append(("add_blockhistory", user_id, admin_id, reason, type_, addinfo, server_id))

    async def get_warning_count(self, server_id: int, user_id: int):
        self.calls.append(("get_warning_count", server_id, user_id))
        return self.remove_warning_result[2]

    def update_warn_max(self, server_id: int, max_warn: int | None):
        self.calls.append(("update_warn_max", server_id, max_warn))


@pytest.mark.asyncio
async def test_add_warning_action_records_history_and_limit_state():
    repository = FakeModerationRepository(warn_max=3, add_warning_result=(2, 1, 3))

    result = await add_warning_action(
        server_id=10,
        user_id=20,
        admin_id=30,
        amount=1,
        reason=None,
        repository=repository,
    )

    assert result.new_count == 3
    assert result.warn_max == 3
    assert result.reason == DEFAULT_REASON
    assert result.reached_limit is True
    assert repository.calls == [
        ("add_warning", 10, 20, 1),
        ("get_warn_max", 10),
        ("add_blockhistory", 20, 30, DEFAULT_REASON, "warn", 1, 10),
    ]


@pytest.mark.asyncio
async def test_remove_warning_action_records_unwarn_history():
    repository = FakeModerationRepository(warn_max=5, remove_warning_result=(4, 2, 2))

    result = await remove_warning_action(
        server_id=10,
        user_id=20,
        admin_id=30,
        amount=2,
        reason="정정",
        repository=repository,
    )

    assert result.new_count == 2
    assert result.warn_max == 5
    assert result.reason == "정정"
    assert repository.calls == [
        ("remove_warning", 10, 20, 2),
        ("get_warn_max", 10),
        ("add_blockhistory", 20, 30, "정정", "unwarn", 2, 10),
    ]


@pytest.mark.asyncio
async def test_finalize_warn_limit_ban_records_ban_and_resets_warning():
    repository = FakeModerationRepository()

    await finalize_warn_limit_ban(
        server_id=10,
        user_id=20,
        bot_user_id=40,
        repository=repository,
    )

    assert repository.calls == [
        ("add_blockhistory", 20, 40, "경고 한도 도달", "ban", 0, 10),
        ("reset_warning", 10, 20),
    ]


def test_parse_timeout_duration_converts_each_supported_unit():
    assert parse_timeout_duration(5, "초") == 5
    assert parse_timeout_duration(5, "분") == 300
    assert parse_timeout_duration(2, "시간") == 7200
    assert parse_timeout_duration(1, "일") == 86400
    assert parse_timeout_duration(1, "주") == 604800


def test_timeout_record_helpers_normalize_reason_and_blockhistory():
    repository = FakeModerationRepository()

    timeout_result = record_timeout_action(
        server_id=10,
        user_id=20,
        admin_id=30,
        duration=600,
        reason=None,
        repository=repository,
    )
    untimeout_result = record_untimeout_action(
        server_id=10,
        user_id=20,
        admin_id=30,
        reason="완료",
        repository=repository,
    )

    assert timeout_result.reason == DEFAULT_REASON
    assert timeout_result.duration == 600
    assert untimeout_result.reason == "완료"
    assert repository.calls == [
        ("add_blockhistory", 20, 30, DEFAULT_REASON, "timeout", 600, 10),
        ("add_blockhistory", 20, 30, "완료", "untimeout", 0, 10),
    ]


@pytest.mark.asyncio
async def test_get_warning_status_reads_count_and_warn_limit():
    repository = FakeModerationRepository(warn_max=5, remove_warning_result=(0, 0, 2))

    result = await get_warning_status(server_id=10, user_id=20, repository=repository)

    assert result == WarningStatusSnapshot(warning_count=2, warn_max=5)
    assert repository.calls == [
        ("get_warning_count", 10, 20),
        ("get_warn_max", 10),
    ]


def test_set_warn_limit_persists_normalized_value():
    repository = FakeModerationRepository()

    result = set_warn_limit(server_id=10, warn_max=None, repository=repository)

    assert result == WarnLimitSettingResult(warn_max=None)
    assert repository.calls == [("update_warn_max", 10, None)]


@pytest.mark.asyncio
async def test_message_handler_warn_path_uses_service_boundary(monkeypatch):
    service_calls = []
    bot = FakeBot()
    block_channel = FakeTextChannel(channel_id=100)
    message_log_channel = FakeTextChannel(channel_id=101)
    bot.channels[100] = block_channel
    bot.channels[101] = message_log_channel

    async def fake_add_warning_action(**kwargs):
        service_calls.append(kwargs)
        service_result = type("ServiceResult", (), {})()
        service_result.new_count = 3
        service_result.delta = 1
        service_result.warn_max = 5
        service_result.reason = "테스트 사유"
        service_result.reached_limit = False
        return service_result

    monkeypatch.setattr(message_handlers_module, "add_warning_action", fake_add_warning_action)
    monkeypatch.setattr(message_handlers_module, "get_block_log_channel_for_guild", lambda bot, guild_id: block_channel)

    member = FakeMember(2, top_role=1)
    message = FakeMessage(
        content="마늘아 경고 <@2> 1 테스트 사유",
        author=FakeAuthor(1, ban_members=True, top_role=10),
        guild=FakeGuild(1, member=member),
        channel=FakeTextChannel(channel_id=20),
    )

    result = await handle_moderation_text_commands(
        message,
        context={
            "friendly_list": [],
            "bot": bot,
            "using_server": 1,
            "message_log": 101,
            "print_time": lambda duration: f"{duration}초",
            "process_commands": lambda msg: None,
            "add_timeout": lambda *args, **kwargs: None,
        },
        error_count=7,
    )

    assert result == ModerationCommandResult(
        status="handled",
        error_count=7,
        stop_processing=True,
        reason_code="warn_processed",
    )
    assert service_calls == [
        {
            "server_id": 1,
            "user_id": 2,
            "admin_id": 1,
            "amount": 1,
            "reason": "테스트 사유",
        }
    ]
    assert message.replies[0]["embed"].title == "경고"
    assert block_channel.sent_embeds[0].title == "경고"
    assert message_log_channel.sent_embeds[0].title == "경고"


@pytest.mark.asyncio
async def test_warn_slash_helper_executes_service_flow(monkeypatch):
    service_calls = []
    finalize_calls = []
    bot = FakeBot()
    block_channel = FakeTextChannel(channel_id=100)
    message_log_channel = FakeTextChannel(channel_id=101)
    bot.channels[100] = block_channel
    bot.channels[101] = message_log_channel

    async def fake_add_warning_action(**kwargs):
        service_calls.append(kwargs)
        result = type("WarnResult", (), {})()
        result.new_count = 3
        result.delta = 1
        result.warn_max = 3
        result.reason = "사유"
        result.reached_limit = True
        return result

    async def fake_finalize_warn_limit_ban(**kwargs):
        finalize_calls.append(kwargs)

    monkeypatch.setattr(slash_moderation_handlers_module, "add_warning_action", fake_add_warning_action)
    monkeypatch.setattr(slash_moderation_handlers_module, "finalize_warn_limit_ban", fake_finalize_warn_limit_ban)
    monkeypatch.setattr(slash_moderation_handlers_module, "get_block_log_channel_for_guild", lambda bot, guild_id: block_channel)

    member = FakeMember(2, top_role=1)
    guild = FakeGuild(1, member=member)
    interaction = FakeSlashInteraction(user=FakeAuthor(1, top_role=10), guild=guild)

    result = await run_warn_slash_command(
        interaction=interaction,
        target_user=type("FakeUser", (), {"id": 2, "mention": "<@2>"})(),
        warning_amount=1,
        reason_text="사유",
        context={
            "friendly_list": [],
            "bot": bot,
            "using_server": 1,
            "message_log": 101,
            "is_blocked": lambda user: (False, None, None),
        },
        error_count=5,
    )

    assert result == ErrorTrackedSlashCommandResult(
        status="completed",
        error_count=5,
        reason_code="warn_processed",
    )
    assert service_calls == [{"server_id": 1, "user_id": 2, "admin_id": 1, "amount": 1, "reason": "사유"}]
    assert finalize_calls == [{"server_id": 1, "user_id": 2, "bot_user_id": 1316579106749681664}]
    assert guild.ban_calls[0]["reason"] == "경고 한도 도달"
    assert interaction.followup.sent[0]["embed"].title == "경고"
    assert interaction.followup.sent[1]["embed"].title == "차단"


@pytest.mark.asyncio
async def test_unwarn_slash_helper_executes_service_flow(monkeypatch):
    service_calls = []
    bot = FakeBot()
    block_channel = FakeTextChannel(channel_id=100)
    bot.channels[100] = block_channel

    async def fake_remove_warning_action(**kwargs):
        service_calls.append(kwargs)
        result = type("WarnResult", (), {})()
        result.new_count = 1
        result.delta = 2
        result.warn_max = 5
        result.reason = "정정"
        return result

    monkeypatch.setattr(slash_moderation_handlers_module, "remove_warning_action", fake_remove_warning_action)
    monkeypatch.setattr(slash_moderation_handlers_module, "get_block_log_channel_for_guild", lambda bot, guild_id: block_channel)

    member = FakeMember(2, top_role=1)
    guild = FakeGuild(1, member=member)
    interaction = FakeSlashInteraction(user=FakeAuthor(1, top_role=10), guild=guild)

    result = await run_unwarn_slash_command(
        interaction=interaction,
        target_user=type("FakeUser", (), {"id": 2, "mention": "<@2>"})(),
        warning_amount=2,
        reason_text="정정",
        context={
            "bot": bot,
            "using_server": 999,
            "message_log": 101,
            "is_blocked": lambda user: (False, None, None),
        },
    )

    assert result == SlashCommandResult(status="completed", reason_code="unwarn_processed")
    assert service_calls == [{"server_id": 1, "user_id": 2, "admin_id": 1, "amount": 2, "reason": "정정"}]
    assert interaction.followup.sent[0]["embed"].title == "경고 차감"


@pytest.mark.asyncio
async def test_timeout_slash_helper_executes_service_flow(monkeypatch):
    add_timeout_calls = []
    record_calls = []
    bot = FakeBot()
    block_channel = FakeTextChannel(channel_id=100)
    bot.channels[100] = block_channel

    def fake_record_timeout_action(**kwargs):
        record_calls.append(kwargs)
        result = type("TimeoutResult", (), {})()
        result.reason = "사유"
        return result

    monkeypatch.setattr(slash_moderation_handlers_module, "record_timeout_action", fake_record_timeout_action)
    monkeypatch.setattr(slash_moderation_handlers_module, "get_block_log_channel_for_guild", lambda bot, guild_id: block_channel)

    async def fake_add_timeout(member, duration, reason):
        add_timeout_calls.append((member.id, duration, reason))

    member = FakeMember(2, top_role=1)
    guild = FakeGuild(1, member=member)
    interaction = FakeSlashInteraction(user=FakeAuthor(1, top_role=10), guild=guild)

    result = await run_timeout_slash_command(
        interaction=interaction,
        target_user=member,
        timeout_value=2,
        timeout_unit="분",
        reason_text="사유",
        private_response="False",
        context={
            "friendly_list": [],
            "bot": bot,
            "using_server": 999,
            "message_log": 101,
            "is_blocked": lambda user: (False, None, None),
            "print_time": lambda seconds: f"{seconds}초",
            "add_timeout": fake_add_timeout,
        },
        error_count=3,
    )

    assert result == ErrorTrackedSlashCommandResult(
        status="completed",
        error_count=3,
        reason_code="timeout_processed",
    )
    assert add_timeout_calls == [(2, 120, "사유")]
    assert record_calls == [{"server_id": 1, "user_id": 2, "admin_id": 1, "duration": 120, "reason": "사유"}]
    assert interaction.followup.sent[0]["embed"].title == "타임아웃"


@pytest.mark.asyncio
async def test_remove_timeout_slash_helper_executes_service_flow(monkeypatch):
    record_calls = []
    bot = FakeBot()
    block_channel = FakeTextChannel(channel_id=100)
    bot.channels[100] = block_channel

    def fake_record_untimeout_action(**kwargs):
        record_calls.append(kwargs)
        result = type("TimeoutResult", (), {})()
        result.reason = "사유"
        return result

    monkeypatch.setattr(slash_moderation_handlers_module, "record_untimeout_action", fake_record_untimeout_action)
    monkeypatch.setattr(slash_moderation_handlers_module, "get_block_log_channel_for_guild", lambda bot, guild_id: block_channel)

    member = FakeMember(2, top_role=1)
    guild = FakeGuild(1, member=member)
    interaction = FakeSlashInteraction(user=FakeAuthor(1, top_role=10), guild=guild)

    result = await run_remove_timeout_slash_command(
        interaction=interaction,
        target_user=member,
        reason_text="사유",
        context={
            "bot": bot,
            "using_server": 999,
            "message_log": 101,
            "is_blocked": lambda user: (False, None, None),
        },
        error_count=8,
    )

    assert result == ErrorTrackedSlashCommandResult(
        status="completed",
        error_count=8,
        reason_code="untimeout_processed",
    )
    assert member.edit_calls == [{"timed_out_until": None, "reason": "사유"}]
    assert record_calls == [{"server_id": 1, "user_id": 2, "admin_id": 1, "reason": "사유"}]
    assert interaction.followup.sent[0]["embed"].title == "타임아웃 해제"


def test_message_handler_source_uses_moderation_services():
    source = Path("bot_app/events/message_handlers.py").read_text(encoding="utf-8")
    main_source = Path("main.py").read_text(encoding="utf-8")
    handler_call_start = main_source.index("moderation_result = await handle_moderation_text_commands(")
    next_call_start = main_source.index("    if moderation_result.stop_processing:", handler_call_start)
    handler_call_source = main_source[handler_call_start:next_call_start]

    assert "from bot_app.services.moderation_service import (" in source
    assert "from bot_app.services.settings_service import (" in source
    assert "add_warning_action(" in source
    assert "remove_warning_action(" in source
    assert "record_timeout_action(" in source
    assert "record_untimeout_action(" in source
    assert 'context["add_warning"]' not in source
    assert 'context["remove_warning"]' not in source
    assert 'context["add_blockhistory"]' not in source
    assert 'context["set_warning"]' not in source
    assert '"add_warning": add_warning' not in handler_call_source
    assert '"remove_warning": remove_warning' not in handler_call_source
    assert '"add_blockhistory": add_blockhistory' not in handler_call_source
    assert '"set_warning": set_warning' not in handler_call_source
    assert "moderation_result.error_count" in main_source


def test_main_slash_moderation_commands_use_service_boundary():
    source = Path("main.py").read_text(encoding="utf-8")
    warn_start = source.index('async def 경고(interaction: discord.Interaction, 사용자: discord.User, 개수: int, 사유: str):')
    warn_end = source.index('@bot.tree.command(name="경고차감"', warn_start)
    unwarn_start = source.index('async def 경고차감(interaction: discord.Interaction, 사용자: discord.User, 개수: int, 사유: str):')
    unwarn_end = source.index('@bot.tree.command(name="경고확인"', unwarn_start)
    timeout_start = source.index('async def timeout(interaction: discord.Interaction, 사용자: discord.Member, 시간: int, 단위: str = "분", 사유: str = "None", 개인응답: str = "False"):')
    timeout_end = source.index('@bot.tree.command(name="타임아웃해제"', timeout_start)
    remove_timeout_start = source.index('async def remove_timeout(interaction: discord.Interaction, 사용자: discord.Member, 사유: str = "None"):')

    warn_source = source[warn_start:warn_end]
    unwarn_source = source[unwarn_start:unwarn_end]
    timeout_source = source[timeout_start:timeout_end]
    remove_timeout_end = source.index('@bot.tree.command(name="동일인여부확인"', remove_timeout_start)
    remove_timeout_source = source[remove_timeout_start:remove_timeout_end]

    assert "from bot_app.commands.slash_moderation_handlers import (" in source
    assert "run_warn_slash_command(" in warn_source
    assert "run_unwarn_slash_command(" in unwarn_source
    assert "run_timeout_slash_command(" in timeout_source
    assert "run_remove_timeout_slash_command(" in remove_timeout_source
    assert "warn_command_result.error_count" in warn_source
    assert "timeout_command_result.error_count" in timeout_source
    assert "remove_timeout_result.error_count" in remove_timeout_source
    assert "add_warning_action(" not in warn_source
    assert "remove_warning_action(" not in unwarn_source
    assert "record_timeout_action(" not in timeout_source
    assert "record_untimeout_action(" not in remove_timeout_source
    assert "add_blockhistory(" not in warn_source
    assert "add_blockhistory(" not in unwarn_source
    assert "add_blockhistory(" not in timeout_source
    assert "add_blockhistory(" not in remove_timeout_source


def test_slash_command_helpers_wrap_blocked_tuple_with_named_state():
    block_state = slash_moderation_handlers_module._resolve_user_block_state(  # noqa: SLF001
        lambda user: (True, "내일", "테스트"),
        object(),
    )

    assert block_state == UserBlockState(
        status="blocked",
        blocked_until_label="내일",
        reason="테스트",
    )


@pytest.mark.asyncio
async def test_moderation_repository_delegates_to_database_helpers(monkeypatch):
    calls = []
    moderation_repository_module = import_module("bot_app.repositories.moderation_repository")

    def fake_get_warn_max(server_id):
        calls.append(("get_warn_max", server_id))
        return 5

    async def fake_add_warning(server_id, user_id, amount):
        calls.append(("add_warning", server_id, user_id, amount))
        return [0, amount, amount]

    async def fake_remove_warning(server_id, user_id, amount):
        calls.append(("remove_warning", server_id, user_id, amount))
        return [amount, amount, 0]

    async def fake_set_warning(server_id, user_id, amount):
        calls.append(("set_warning", server_id, user_id, amount))
        return amount

    async def fake_load_warning(server_id, user_id):
        calls.append(("load_warning", server_id, user_id))
        return 4

    def fake_update_warn_max(server_id, max_warn):
        calls.append(("update_warn_max", server_id, max_warn))

    def fake_add_blockhistory(user_id, admin_id, reason, type_, addinfo, server_id):
        calls.append(("add_blockhistory", user_id, admin_id, reason, type_, addinfo, server_id))

    monkeypatch.setattr(moderation_repository_module, "get_warn_max", fake_get_warn_max)
    monkeypatch.setattr(moderation_repository_module, "add_warning", fake_add_warning)
    monkeypatch.setattr(moderation_repository_module, "remove_warning", fake_remove_warning)
    monkeypatch.setattr(moderation_repository_module, "set_warning", fake_set_warning)
    monkeypatch.setattr(moderation_repository_module, "load_warning", fake_load_warning)
    monkeypatch.setattr(moderation_repository_module, "update_warn_max", fake_update_warn_max)
    monkeypatch.setattr(moderation_repository_module, "add_blockhistory", fake_add_blockhistory)

    repository = ModerationRepository()

    assert repository.get_warn_max(1) == 5
    assert await repository.add_warning(1, 2, 3) == [0, 3, 3]
    assert await repository.remove_warning(1, 2, 3) == [3, 3, 0]
    assert await repository.reset_warning(1, 2) == 0
    assert await repository.get_warning_count(1, 2) == 4
    repository.update_warn_max(1, 7)
    repository.add_blockhistory(2, 3, "사유", "warn", 1, 1)

    assert calls == [
        ("get_warn_max", 1),
        ("add_warning", 1, 2, 3),
        ("remove_warning", 1, 2, 3),
        ("set_warning", 1, 2, 0),
        ("load_warning", 1, 2),
        ("update_warn_max", 1, 7),
        ("add_blockhistory", 2, 3, "사유", "warn", 1, 1),
    ]
