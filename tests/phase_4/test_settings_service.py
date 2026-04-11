from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import discord

from bot_app.repositories.settings_repository import SettingsRepository
from bot_app.services.settings_service import (
    get_automod_setting,
    get_block_log_channel_for_guild,
    is_automod_exempt_channel,
    update_guild_log_channels,
)
from bot_app.types.readability_contracts import AutomodConfig, AutomodExemptionResult, AutomodRuleConfig, GuildLogChannelSelection
from tests.helpers.fakes import FakeBot, FakeTextChannel


class FakeSettingsRepository:
    def __init__(self, *, automod=None, exception_channel_ids=None, block_log_channel_id=0):
        self.automod = automod or AutomodConfig(
            political=AutomodRuleConfig(enabled=False, action=0),
            sexual=AutomodRuleConfig(enabled=False, action=0),
            invite_link=AutomodRuleConfig(enabled=True, action=60),
            mention=AutomodRuleConfig(enabled=False, action=0),
            whitelist_permission="admin",
        )
        self.exception_channel_ids = set(exception_channel_ids or set())
        self.block_log_channel_id = block_log_channel_id
        self.calls = []

    def get_automod(self, server_id: int):
        self.calls.append(("get_automod", server_id))
        return self.automod

    def is_automod_exception_channel(self, server_id: int, channel_id: int):
        self.calls.append(("is_automod_exception_channel", server_id, channel_id))
        return channel_id in self.exception_channel_ids

    def get_block_log_channel(self, server_id: int):
        self.calls.append(("get_block_log_channel", server_id))
        return self.block_log_channel_id

    def update_guild_log_channels(self, server_id: int, selection: GuildLogChannelSelection):
        self.calls.append(("update_guild_log_channels", server_id, selection))


def test_is_automod_exempt_channel_checks_direct_channel_first():
    repository = FakeSettingsRepository(exception_channel_ids={20})
    channel = SimpleNamespace(id=20, category=None)

    assert is_automod_exempt_channel(1, channel, repository=repository) == AutomodExemptionResult(
        status="exempt",
        matched_scope="channel",
        matched_channel_id=20,
    )
    assert repository.calls == [("is_automod_exception_channel", 1, 20)]


def test_is_automod_exempt_channel_checks_normal_channel_category():
    repository = FakeSettingsRepository(exception_channel_ids={30})
    channel = SimpleNamespace(id=20, category=SimpleNamespace(id=30))

    assert is_automod_exempt_channel(1, channel, repository=repository) == AutomodExemptionResult(
        status="exempt",
        matched_scope="category",
        matched_channel_id=30,
    )
    assert repository.calls == [
        ("is_automod_exception_channel", 1, 20),
        ("is_automod_exception_channel", 1, 30),
    ]


def test_is_automod_exempt_channel_checks_thread_parent_and_category(monkeypatch):
    repository = FakeSettingsRepository(exception_channel_ids={40})
    parent = SimpleNamespace(id=30, category=SimpleNamespace(id=40))
    fake_thread_type = type("FakeThreadType", (), {})
    monkeypatch.setattr(discord, "Thread", fake_thread_type)
    thread = fake_thread_type()
    thread.id = 20
    thread.parent = parent

    assert is_automod_exempt_channel(1, thread, repository=repository) == AutomodExemptionResult(
        status="exempt",
        matched_scope="thread_parent_category",
        matched_channel_id=40,
    )
    assert repository.calls == [
        ("is_automod_exception_channel", 1, 20),
        ("is_automod_exception_channel", 1, 30),
        ("is_automod_exception_channel", 1, 40),
    ]


def test_settings_service_returns_automod_setting_and_block_log_channel():
    repository = FakeSettingsRepository(
        automod=AutomodConfig(
            political=AutomodRuleConfig(enabled=False, action=0),
            sexual=AutomodRuleConfig(enabled=False, action=0),
            invite_link=AutomodRuleConfig(enabled=False, action=0),
            mention=AutomodRuleConfig(enabled=False, action=0),
            whitelist_permission="admin",
        ),
        block_log_channel_id=100,
    )
    bot = FakeBot()
    channel = FakeTextChannel(channel_id=100)
    bot.channels[100] = channel

    assert get_automod_setting(1, repository=repository) == repository.automod
    assert get_block_log_channel_for_guild(bot, 1, repository=repository) is channel
    assert repository.calls == [
        ("get_automod", 1),
        ("get_block_log_channel", 1),
    ]


def test_settings_service_updates_guild_log_channels_with_named_contract():
    repository = FakeSettingsRepository()
    selection = GuildLogChannelSelection(editdelete=11, reaction=12, role=13, image=14, block=15)

    result = update_guild_log_channels(server_id=1, selection=selection, repository=repository)

    assert result == selection
    assert repository.calls == [
        ("update_guild_log_channels", 1, selection),
    ]


def test_message_handler_and_main_use_settings_services():
    source = Path("bot_app/events/message_handlers.py").read_text(encoding="utf-8")
    main_source = Path("main.py").read_text(encoding="utf-8")
    moderation_call_start = main_source.index("moderation_result = await handle_moderation_text_commands(")
    moderation_call_end = main_source.index("    if moderation_result.stop_processing:", moderation_call_start)
    moderation_call_source = main_source[moderation_call_start:moderation_call_end]
    automod_call_start = main_source.index("    automod_result = await handle_automod_message(")
    automod_call_end = main_source.index("    if automod_result.stop_processing:", automod_call_start)
    automod_call_source = main_source[automod_call_start:automod_call_end]

    assert "get_block_log_channel_for_guild(" in source
    assert "is_automod_exempt_channel(" in source
    assert "get_automod_setting(" in source
    assert "AutomodExemptionResult" in Path("bot_app/services/settings_service.py").read_text(encoding="utf-8")
    assert "automod_setting.invite_link.enabled" in source
    assert 'automod_setting["invite_link"][0]' not in source
    assert 'context["get_block_log_channel"]' not in source
    assert 'context["get_automod_exception_channel"]' not in source
    assert 'context["get_automod"]' not in source
    assert '"get_block_log_channel": get_block_log_channel' not in moderation_call_source
    assert '"get_automod_exception_channel": get_automod_exception_channel' not in automod_call_source
    assert '"get_automod": get_automod' not in automod_call_source


def test_settings_repository_delegates_to_database_helpers(monkeypatch):
    calls = []
    settings_repository_module = import_module("bot_app.repositories.settings_repository")

    def fake_get_automod(server_id):
        calls.append(("get_automod", server_id))
        return {
            "political": [False, 0],
            "sexual": [False, 0],
            "invite_link": [False, 0],
            "mention": [False, 0],
            "whitelist_permission": "admin",
        }

    def fake_get_automod_exception_channel(server_id, channel_id):
        calls.append(("get_automod_exception_channel", server_id, channel_id))
        return True

    def fake_get_block_log_channel(server_id):
        calls.append(("get_block_log_channel", server_id))
        return 999

    def fake_update_log_channel(server_id, editdelete, reaction, role, image):
        calls.append(("update_log_channel", server_id, editdelete, reaction, role, image))

    def fake_update_block_log_channel(server_id, channel_id):
        calls.append(("update_block_log_channel", server_id, channel_id))

    monkeypatch.setattr(settings_repository_module, "get_automod", fake_get_automod)
    monkeypatch.setattr(settings_repository_module, "get_automod_exception_channel", fake_get_automod_exception_channel)
    monkeypatch.setattr(settings_repository_module, "get_block_log_channel", fake_get_block_log_channel)
    monkeypatch.setattr(settings_repository_module, "update_log_channel", fake_update_log_channel)
    monkeypatch.setattr(settings_repository_module, "update_block_log_channel", fake_update_block_log_channel)

    repository = SettingsRepository()

    assert repository.get_automod(1) == AutomodConfig(
        political=AutomodRuleConfig(enabled=False, action=0),
        sexual=AutomodRuleConfig(enabled=False, action=0),
        invite_link=AutomodRuleConfig(enabled=False, action=0),
        mention=AutomodRuleConfig(enabled=False, action=0),
        whitelist_permission="admin",
    )
    assert repository.is_automod_exception_channel(1, 2) is True
    assert repository.get_block_log_channel(1) == 999
    repository.update_guild_log_channels(
        1,
        GuildLogChannelSelection(editdelete=11, reaction=12, role=13, image=14, block=15),
    )
    assert calls == [
        ("get_automod", 1),
        ("get_automod_exception_channel", 1, 2),
        ("get_block_log_channel", 1),
        ("update_log_channel", 1, 11, 12, 13, 14),
        ("update_block_log_channel", 1, 15),
    ]
