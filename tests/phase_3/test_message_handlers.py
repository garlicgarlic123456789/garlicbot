from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import discord
import pytest

from bot_app.events.message_handlers import (
    handle_automod_message,
    handle_moderation_text_commands,
    handle_using_server_role_watchers,
)
from tests.helpers.fakes import FakeBot, FakeRole, FakeTextChannel


class FakePermissions:
    def __init__(self, *, ban_members=False, moderate_members=False, manage_messages=False):
        self.ban_members = ban_members
        self.moderate_members = moderate_members
        self.manage_messages = manage_messages


class FakeAuthor:
    def __init__(self, author_id: int, *, bot: bool = False, ban_members=False, moderate_members=False, top_role=10):
        self.id = author_id
        self.bot = bot
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
        self.edit_calls = []

    def get_member(self, member_id):
        return self._member

    async def ban(self, member, *, reason=None, delete_message_days=0):
        return None

    async def edit(self, **kwargs):
        self.edit_calls.append(kwargs)


class FakeChannel(FakeTextChannel):
    def __init__(self, *, channel_id: int, category=None):
        super().__init__(channel_id=channel_id)
        self.category = category
        self.parent = None


class FakeMessage:
    def __init__(self, *, content: str, author, guild, channel, role_mentions=None, snapshots=None):
        self.content = content
        self.author = author
        self.guild = guild
        self.channel = channel
        self.role_mentions = list(role_mentions or [])
        self.message_snapshots = list(snapshots or [])
        self.replies = []

    async def reply(self, content=None, *, embed=None, mention_author=False):
        self.replies.append({"content": content, "embed": embed, "mention_author": mention_author})


@pytest.mark.asyncio
async def test_handle_moderation_text_commands_processes_commands_when_plain_message():
    process_calls = []
    message = FakeMessage(
        content="그냥 메시지",
        author=FakeAuthor(1),
        guild=FakeGuild(1, member=FakeMember(2)),
        channel=FakeChannel(channel_id=20),
    )

    async def fake_process_commands(msg):
        process_calls.append(msg)

    handled, error_count = await handle_moderation_text_commands(
        message,
        context={
            "friendly_list": [],
            "get_warn_max": lambda guild_id: None,
            "add_warning": lambda *args: None,
            "add_blockhistory": lambda *args: None,
            "bot": FakeBot(),
            "get_block_log_channel": lambda guild_id: 0,
            "using_server": 1,
            "message_log": 100,
            "set_warning": lambda *args: None,
            "remove_warning": lambda *args: None,
            "print_time": lambda duration: f"{duration}초",
            "process_commands": fake_process_commands,
            "add_timeout": lambda *args, **kwargs: None,
        },
        error_count=7,
    )

    assert handled is False
    assert error_count == 7
    assert process_calls == [message]


@pytest.mark.asyncio
async def test_handle_moderation_text_commands_warn_permission_error():
    member = FakeMember(2)
    message = FakeMessage(
        content="마늘아 경고 <@2> 1 사유",
        author=FakeAuthor(1, ban_members=False),
        guild=FakeGuild(1, member=member),
        channel=FakeChannel(channel_id=20),
    )

    handled, error_count = await handle_moderation_text_commands(
        message,
        context={
            "friendly_list": [],
            "get_warn_max": lambda guild_id: None,
            "add_warning": lambda *args: None,
            "add_blockhistory": lambda *args: None,
            "bot": FakeBot(),
            "get_block_log_channel": lambda guild_id: 0,
            "using_server": 1,
            "message_log": 100,
            "set_warning": lambda *args: None,
            "remove_warning": lambda *args: None,
            "print_time": lambda duration: f"{duration}초",
            "process_commands": lambda msg: None,
            "add_timeout": lambda *args, **kwargs: None,
        },
        error_count=3,
    )

    assert handled is True
    assert error_count == 3
    assert message.replies[0]["embed"].title == "오류"
    assert "권한이 부족합니다" in message.replies[0]["embed"].description


@pytest.mark.asyncio
async def test_handle_using_server_role_watchers_sends_deprecated_role_notice():
    channel = FakeChannel(channel_id=20)
    message = FakeMessage(
        content="<@&1375687128708677682> 테스트",
        author=FakeAuthor(1),
        guild=FakeGuild(1),
        channel=channel,
        role_mentions=[],
    )

    await handle_using_server_role_watchers(
        message,
        context={
            "using_server": 1,
            "do_mention_role": {999},
            "mention_timestamps": defaultdict(list),
            "handle_spamming": lambda *args, **kwargs: None,
        },
    )

    assert channel.sent_embeds[0].title == "안내"


@pytest.mark.asyncio
async def test_handle_automod_message_returns_true_for_exception_channel():
    message = FakeMessage(
        content="테스트",
        author=FakeAuthor(1),
        guild=FakeGuild(1),
        channel=FakeChannel(channel_id=20),
    )

    handled = await handle_automod_message(
        message,
        context={
            "get_automod_exception_channel": lambda guild_id, channel_id: channel_id == 20,
            "get_automod": lambda guild_id: {"invite_link": [False, 0], "political": [False, 0], "sexual": [False, 0], "mention": [False, 0]},
            "handle_spamming": lambda *args, **kwargs: None,
            "using_server": 1,
            "automod_keyword": [],
            "automod_keyword2": [],
            "automod_keyword3": [],
            "automod_keyword4": [],
            "automod_keyword5": [],
            "automod_keyword6": [],
            "automod_keyword7": [],
            "automod_keyword8": [],
            "automod_keyword9": [],
            "automod_keyword10": [],
            "automod_keyword11": [],
            "automod_reason": "",
            "automod_reason2": "",
            "automod_reason3": "",
            "automod_reason4": "",
            "automod_reason5": "",
            "automod_reason6": "",
            "automod_reason7": "",
            "automod_reason8": "",
            "automod_reason9": "",
            "automod_reason10": "",
            "automod_reason11": "",
            "raid_keyword1": [],
            "do_mention_role2": [],
        },
    )

    assert handled is True


@pytest.mark.asyncio
async def test_handle_automod_message_handles_invite_link():
    spamming_calls = []
    message = FakeMessage(
        content="discord.gg/test",
        author=FakeAuthor(1),
        guild=FakeGuild(1),
        channel=FakeChannel(channel_id=20),
    )

    async def fake_handle_spamming(*args):
        spamming_calls.append(args)

    handled = await handle_automod_message(
        message,
        context={
            "get_automod_exception_channel": lambda guild_id, channel_id: False,
            "get_automod": lambda guild_id: {"invite_link": [True, 60], "political": [False, 0], "sexual": [False, 0], "mention": [False, 0]},
            "handle_spamming": fake_handle_spamming,
            "using_server": 1,
            "automod_keyword": [],
            "automod_keyword2": [],
            "automod_keyword3": [],
            "automod_keyword4": [],
            "automod_keyword5": [],
            "automod_keyword6": [],
            "automod_keyword7": [],
            "automod_keyword8": [],
            "automod_keyword9": [],
            "automod_keyword10": [],
            "automod_keyword11": [],
            "automod_reason": "",
            "automod_reason2": "",
            "automod_reason3": "",
            "automod_reason4": "",
            "automod_reason5": "",
            "automod_reason6": "",
            "automod_reason7": "",
            "automod_reason8": "",
            "automod_reason9": "",
            "automod_reason10": "",
            "automod_reason11": "",
            "raid_keyword1": [],
            "do_mention_role2": [],
        },
    )

    assert handled is True
    assert spamming_calls


def test_main_keeps_message_handler_boundary():
    source = Path("main.py").read_text(encoding="utf-8")

    assert "from bot_app.events.message_handlers import (" in source
    assert "handle_moderation_text_commands(" in source
    assert "handle_using_server_role_watchers(" in source
    assert "handle_automod_message(" in source
