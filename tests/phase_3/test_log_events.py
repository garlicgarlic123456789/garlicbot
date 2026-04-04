import discord

from bot_app.events.log_events import (
    build_reaction_embed,
    register_log_events,
    should_skip_log_channel,
    truncate_log_content,
)
from tests.helpers.fakes import FakeBot


class FakeEmoji:
    def __init__(self, name: str, *, custom: bool = False, animated: bool = False, emoji_id: int = 123):
        self.name = name
        self._custom = custom
        self.animated = animated
        self.id = emoji_id

    def is_custom_emoji(self):
        return self._custom


def test_should_skip_log_channel_checks_membership():
    assert should_skip_log_channel(10, {10, 20}) is True
    assert should_skip_log_channel(30, {10, 20}) is False


def test_truncate_log_content_respects_limit_and_fallback():
    assert truncate_log_content("", fallback="없음") == "없음"
    assert truncate_log_content("a" * 1005, fallback="없음").endswith("(이후 생략)")


def test_build_reaction_embed_supports_unicode_emoji():
    payload = type(
        "Payload",
        (),
        {
            "user_id": 1,
            "guild_id": 2,
            "channel_id": 3,
            "message_id": 4,
            "emoji": FakeEmoji("😀"),
        },
    )()

    embed = build_reaction_embed(payload, title="반응 추가됨", color=discord.Color.blue())

    assert embed.title == "반응 추가됨"
    assert embed.fields[1].value == "😀"
    assert "https://discord.com/channels/2/3/4" in embed.fields[2].value


def test_register_log_events_registers_all_log_handlers():
    bot = FakeBot()

    register_log_events(
        bot,
        {
            "no_log_channel": set(),
            "get_log_channel": lambda guild_id: {"editdelete": None, "reaction": None, "image": None},
            "handle_spamming": None,
            "using_server": 0,
            "automod_keyword": [],
            "automod_keyword2": [],
            "automod_keyword3": [],
            "automod_keyword4": [],
            "automod_keyword5": [],
            "automod_keyword7": [],
            "automod_keyword8": [],
            "automod_keyword9": [],
            "automod_keyword10": [],
            "automod_keyword11": [],
            "raid_keyword1": [],
            "automod_reason": "",
            "automod_reason2": "",
            "automod_reason3": "",
            "automod_reason4": "",
            "automod_reason5": "",
            "automod_reason7": "",
            "automod_reason8": "",
            "automod_reason9": "",
            "automod_reason10": "",
            "automod_reason11": "",
        },
    )

    assert set(bot.registered_events) == {
        "on_raw_message_delete",
        "on_message_delete",
        "on_raw_message_edit",
        "on_raw_reaction_add",
        "on_raw_reaction_remove",
    }
