from datetime import datetime
from pathlib import Path

import discord
import pytest

from bot_app.events.message_pipeline import (
    handle_developer_text_commands,
    handle_message_delete_command,
    record_chat_analyze_message,
    run_message_preprocessing,
    should_ignore_direct_message,
)
from tests.helpers.fakes import FakeBot, FakeTextChannel


class FakePermissions:
    def __init__(self, *, manage_messages: bool):
        self.manage_messages = manage_messages


class FakePipelineAuthor:
    def __init__(self, author_id: int, *, bot: bool = False, manage_messages: bool = False):
        self.id = author_id
        self.bot = bot
        self.guild_permissions = FakePermissions(manage_messages=manage_messages)
        self.sent_messages = []

    async def send(self, content=None, *, embed=None):
        self.sent_messages.append({"content": content, "embed": embed})


class FakePipelineGuild:
    def __init__(self, guild_id: int):
        self.id = guild_id


class FakeOriginalMessage:
    def __init__(self, *, guild_id: int, author_id: int):
        self.guild = FakePipelineGuild(guild_id)
        self.author = type("OriginalAuthor", (), {"id": author_id})()
        self.deleted = False

    async def delete(self):
        self.deleted = True


class FakePipelineChannel(FakeTextChannel):
    def __init__(self, *, channel_id: int, original_message=None):
        super().__init__(channel_id=channel_id)
        self.original_message = original_message

    async def fetch_message(self, message_id):
        if self.original_message is None:
            raise discord.NotFound(response=None, message="not found")
        return self.original_message


class FakePipelineMessage:
    def __init__(
        self,
        *,
        content: str,
        author,
        guild,
        channel,
        reference_message_id: int | None = None,
    ):
        self.content = content
        self.author = author
        self.guild = guild
        self.channel = channel
        self.reference = (
            type("Reference", (), {"message_id": reference_message_id})()
            if reference_message_id is not None
            else None
        )
        self.replies = []

    async def reply(self, content=None, *, embed=None, mention_author=False):
        self.replies.append(
            {"content": content, "embed": embed, "mention_author": mention_author}
        )


@pytest.mark.asyncio
async def test_record_chat_analyze_message_accumulates_expected_buckets():
    chat_analyze_count = {}
    chat_analyze_count_channel = {}
    guild = FakePipelineGuild(10)
    channel = FakePipelineChannel(channel_id=20)
    author = FakePipelineAuthor(30)
    message = FakePipelineMessage(content="안녕", author=author, guild=guild, channel=channel)

    async def fake_get_chat_analyze_onoff(guild_id):
        assert guild_id == 10
        return True

    await record_chat_analyze_message(
        message,
        get_chat_analyze_onoff=fake_get_chat_analyze_onoff,
        chat_analyze_count=chat_analyze_count,
        chat_analyze_count_channel=chat_analyze_count_channel,
        now_factory=lambda: datetime(2026, 4, 5, 22, 55),
    )

    assert chat_analyze_count == {"2026-04-05 22:55": {10: [30]}}
    assert chat_analyze_count_channel == {"2026-04-05 22:55": {10: {20: [30]}}}


@pytest.mark.asyncio
async def test_handle_developer_text_commands_processes_account_add_command():
    added_relations = []
    author = FakePipelineAuthor(99)
    message = FakePipelineMessage(
        content="!부계추가 100 200",
        author=author,
        guild=FakePipelineGuild(1),
        channel=FakePipelineChannel(channel_id=1),
    )

    handled = await handle_developer_text_commands(
        message,
        developer=99,
        add_account_relation=lambda main_id, sub_id: added_relations.append((main_id, sub_id)),
        remove_account_relation=lambda *args: None,
        get_related_accounts=lambda user_id: [],
        add_blacklist=lambda *args: None,
        check_blacklist=lambda user_id: (False,),
        delete_blacklist=lambda *args: None,
        update_premium=lambda *args: None,
    )

    assert handled is True
    assert added_relations == [(100, 200)]
    assert message.replies[0]["content"] == "처리되었습니다."


@pytest.mark.asyncio
async def test_handle_developer_text_commands_processes_blacklist_lookup():
    author = FakePipelineAuthor(99)
    message = FakePipelineMessage(
        content="!블리확인 123",
        author=author,
        guild=FakePipelineGuild(1),
        channel=FakePipelineChannel(channel_id=1),
    )

    handled = await handle_developer_text_commands(
        message,
        developer=99,
        add_account_relation=lambda *args: None,
        remove_account_relation=lambda *args: None,
        get_related_accounts=lambda user_id: [],
        add_blacklist=lambda *args: None,
        check_blacklist=lambda user_id: (True, "사유", "링크", 1, 777, 5),
        delete_blacklist=lambda *args: None,
        update_premium=lambda *args: None,
    )

    assert handled is True
    assert "블랙리스트에 존재하는 유저입니다." in message.replies[0]["content"]
    assert "123" in message.replies[0]["content"]


@pytest.mark.asyncio
async def test_handle_message_delete_command_replies_when_original_missing():
    author = FakePipelineAuthor(10, manage_messages=True)
    message = FakePipelineMessage(
        content="!메시지삭제",
        author=author,
        guild=FakePipelineGuild(1),
        channel=FakePipelineChannel(channel_id=20, original_message=None),
        reference_message_id=999,
    )

    handled = await handle_message_delete_command(
        message,
        bot=FakeBot(),
        using_server=1,
        message_log=100,
    )

    assert handled is True
    assert message.replies[0]["content"] == "**[오류!]** 원본 메시지를 찾을 수 없습니다."


@pytest.mark.asyncio
async def test_handle_message_delete_command_deletes_original_and_logs():
    bot = FakeBot()
    log_channel = FakeTextChannel(channel_id=100)
    bot.channels[100] = log_channel

    original_message = FakeOriginalMessage(guild_id=1, author_id=77)
    author = FakePipelineAuthor(10, manage_messages=True)
    channel = FakePipelineChannel(channel_id=20, original_message=original_message)
    message = FakePipelineMessage(
        content="!메시지삭제 사유",
        author=author,
        guild=FakePipelineGuild(1),
        channel=channel,
        reference_message_id=999,
    )

    handled = await handle_message_delete_command(
        message,
        bot=bot,
        using_server=1,
        message_log=100,
    )

    assert handled is True
    assert original_message.deleted is True
    assert message.replies[0]["content"] == "처리되었습니다."
    assert log_channel.sent_embeds[0].title == "메시지 삭제"
    assert log_channel.sent_embeds[0].fields[3].value == "<@77>"


@pytest.mark.asyncio
async def test_run_message_preprocessing_keeps_flow_after_developer_command():
    chat_analyze_count = {}
    chat_analyze_count_channel = {}
    author = FakePipelineAuthor(99)
    message = FakePipelineMessage(
        content="!부계추가 100 200",
        author=author,
        guild=FakePipelineGuild(1),
        channel=FakePipelineChannel(channel_id=20),
    )
    added_relations = []

    async def fake_get_chat_analyze_onoff(guild_id):
        return True

    should_stop = await run_message_preprocessing(
        message,
        get_chat_analyze_onoff=fake_get_chat_analyze_onoff,
        chat_analyze_count=chat_analyze_count,
        chat_analyze_count_channel=chat_analyze_count_channel,
        developer=99,
        add_account_relation=lambda main_id, sub_id: added_relations.append((main_id, sub_id)),
        remove_account_relation=lambda *args: None,
        get_related_accounts=lambda user_id: [],
        add_blacklist=lambda *args: None,
        check_blacklist=lambda user_id: (False,),
        delete_blacklist=lambda *args: None,
        update_premium=lambda *args: None,
        bot=FakeBot(),
        using_server=1,
        message_log=100,
    )

    assert should_stop is False
    assert added_relations == [(100, 200)]
    assert message.replies[0]["content"] == "처리되었습니다."
    assert len(chat_analyze_count) == 1
    formatted_time = next(iter(chat_analyze_count))
    assert chat_analyze_count[formatted_time][1] == [99]
    assert chat_analyze_count_channel[formatted_time][1][20] == [99]


@pytest.mark.asyncio
async def test_run_message_preprocessing_stops_when_delete_command_is_handled():
    bot = FakeBot()
    log_channel = FakeTextChannel(channel_id=100)
    bot.channels[100] = log_channel
    original_message = FakeOriginalMessage(guild_id=1, author_id=77)
    author = FakePipelineAuthor(10, manage_messages=True)
    message = FakePipelineMessage(
        content="!메시지삭제",
        author=author,
        guild=FakePipelineGuild(1),
        channel=FakePipelineChannel(channel_id=20, original_message=original_message),
        reference_message_id=999,
    )

    async def fake_get_chat_analyze_onoff(guild_id):
        return False

    should_stop = await run_message_preprocessing(
        message,
        get_chat_analyze_onoff=fake_get_chat_analyze_onoff,
        chat_analyze_count={},
        chat_analyze_count_channel={},
        developer=99,
        add_account_relation=lambda *args: None,
        remove_account_relation=lambda *args: None,
        get_related_accounts=lambda user_id: [],
        add_blacklist=lambda *args: None,
        check_blacklist=lambda user_id: (False,),
        delete_blacklist=lambda *args: None,
        update_premium=lambda *args: None,
        bot=bot,
        using_server=1,
        message_log=100,
    )

    assert should_stop is True
    assert original_message.deleted is True
    assert message.replies[0]["content"] == "처리되었습니다."


def test_should_ignore_direct_message_checks_guild_presence():
    dm_message = type("Message", (), {"guild": None})()
    guild_message = type("Message", (), {"guild": object()})()

    assert should_ignore_direct_message(dm_message) is True
    assert should_ignore_direct_message(guild_message) is False


def test_main_keeps_message_pipeline_boundary():
    source = Path("main.py").read_text(encoding="utf-8")

    assert "from bot_app.events.message_pipeline import (" in source
    assert "run_message_preprocessing(" in source
