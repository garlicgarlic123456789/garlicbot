from importlib import import_module
from pathlib import Path

import pytest

from bot_app.events import message_handlers as message_handlers_module
from bot_app.events.message_handlers import handle_moderation_text_commands
from bot_app.repositories.moderation_repository import ModerationRepository
from bot_app.services.moderation_service import (
    DEFAULT_REASON,
    add_warning_action,
    finalize_warn_limit_ban,
    parse_timeout_duration,
    record_timeout_action,
    record_untimeout_action,
    remove_warning_action,
)
from tests.helpers.fakes import FakeBot, FakeTextChannel


class FakePermissions:
    def __init__(self, *, ban_members=False, moderate_members=False):
        self.ban_members = ban_members
        self.moderate_members = moderate_members


class FakeAuthor:
    def __init__(self, author_id: int, *, ban_members=False, moderate_members=False, top_role=10):
        self.id = author_id
        self.bot = False
        self.mention = f"<@{author_id}>"
        self.guild_permissions = FakePermissions(
            ban_members=ban_members,
            moderate_members=moderate_members,
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

    handled, error_count = await handle_moderation_text_commands(
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

    assert handled is True
    assert error_count == 7
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


def test_message_handler_source_uses_moderation_services():
    source = Path("bot_app/events/message_handlers.py").read_text(encoding="utf-8")
    main_source = Path("main.py").read_text(encoding="utf-8")
    handler_call_start = main_source.index("handled, error = await handle_moderation_text_commands(")
    next_call_start = main_source.index("    if handled:", handler_call_start)
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


def test_main_slash_moderation_commands_use_service_boundary():
    source = Path("main.py").read_text(encoding="utf-8")
    warn_start = source.index('async def 경고(interaction: discord.Interaction, 사용자: discord.User, 개수: int, 사유: str):')
    warn_end = source.index('@bot.tree.command(name="경고차감"', warn_start)
    unwarn_start = source.index('async def 경고차감(interaction: discord.Interaction, 사용자: discord.User, 개수: int, 사유: str):')
    unwarn_end = source.index('@bot.tree.command(name="경고확인"', unwarn_start)
    timeout_start = source.index('async def timeout(interaction: discord.Interaction, 사용자: discord.Member, 시간: int, 단위: str = "분", 사유: str = "None", 개인응답: str = "False"):')
    timeout_end = source.index('@bot.tree.command(name="타임아웃해제"', timeout_start)
    remove_timeout_start = source.index('async def remove_timeout(interaction: discord.Interaction, 사용자: discord.Member, 사유: str = "None"):')
    legacy_block_end = source.index("'''", remove_timeout_start)

    warn_source = source[warn_start:warn_end]
    unwarn_source = source[unwarn_start:unwarn_end]
    timeout_source = source[timeout_start:timeout_end]
    remove_timeout_source = source[remove_timeout_start:legacy_block_end]

    assert "from bot_app.services.moderation_service import (" in source
    assert "from bot_app.services.settings_service import get_block_log_channel_for_guild" in source
    assert "add_warning_action(" in warn_source
    assert "finalize_warn_limit_ban(" in warn_source
    assert "remove_warning_action(" in unwarn_source
    assert "record_timeout_action(" in timeout_source
    assert "record_untimeout_action(" in remove_timeout_source
    assert "parse_timeout_duration(" in timeout_source
    assert "get_block_log_channel_for_guild(" in warn_source
    assert "get_block_log_channel_for_guild(" in unwarn_source
    assert "get_block_log_channel_for_guild(" in timeout_source
    assert "get_block_log_channel_for_guild(" in remove_timeout_source
    assert "await add_warning(" not in warn_source
    assert "await remove_warning(" not in unwarn_source
    assert "add_blockhistory(" not in warn_source
    assert "add_blockhistory(" not in unwarn_source
    assert "add_blockhistory(" not in timeout_source
    assert "add_blockhistory(" not in remove_timeout_source
    assert "get_warn_max(" not in warn_source
    assert "get_warn_max(" not in unwarn_source
    assert "set_warning(" not in warn_source


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

    def fake_add_blockhistory(user_id, admin_id, reason, type_, addinfo, server_id):
        calls.append(("add_blockhistory", user_id, admin_id, reason, type_, addinfo, server_id))

    monkeypatch.setattr(moderation_repository_module, "get_warn_max", fake_get_warn_max)
    monkeypatch.setattr(moderation_repository_module, "add_warning", fake_add_warning)
    monkeypatch.setattr(moderation_repository_module, "remove_warning", fake_remove_warning)
    monkeypatch.setattr(moderation_repository_module, "set_warning", fake_set_warning)
    monkeypatch.setattr(moderation_repository_module, "add_blockhistory", fake_add_blockhistory)

    repository = ModerationRepository()

    assert repository.get_warn_max(1) == 5
    assert await repository.add_warning(1, 2, 3) == [0, 3, 3]
    assert await repository.remove_warning(1, 2, 3) == [3, 3, 0]
    assert await repository.reset_warning(1, 2) == 0
    repository.add_blockhistory(2, 3, "사유", "warn", 1, 1)

    assert calls == [
        ("get_warn_max", 1),
        ("add_warning", 1, 2, 3),
        ("remove_warning", 1, 2, 3),
        ("set_warning", 1, 2, 0),
        ("add_blockhistory", 2, 3, "사유", "warn", 1, 1),
    ]
