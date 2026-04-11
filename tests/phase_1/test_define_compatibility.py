import os
import subprocess
import sys
from pathlib import Path

import discord
import pytest

from bot_app.ai.gemini_runtime import LazyGeminiClient
from bot_app.config.constants import build_allowed_mentions
from bot_app.config.env import (
    get_gemini_api_key,
    get_train_arrivals_api_key,
    get_train_timetable_api_key,
)
from bot_app.config.ids import (
    DEVELOPER_USER_ID,
    MESSAGE_LOG_CHANNEL_ID,
    RECORD_CHANNEL_ID,
    USING_SERVER_ID,
)
from bot_app.core import runtime_state
from bot_app.core.bot_factory import build_bot, build_intents
from commands import define


def test_define_reexports_phase1_config_ids():
    assert define.developer == DEVELOPER_USER_ID
    assert define.using_server == USING_SERVER_ID
    assert define.record_channel == RECORD_CHANNEL_ID
    assert define.message_log == MESSAGE_LOG_CHANNEL_ID


def test_define_uses_same_environment_values_as_config_helpers():
    assert define.train_timetable_api_key == get_train_timetable_api_key()
    assert define.train_arrivals_api_key == get_train_arrivals_api_key()
    assert define.gemini_api_key == get_gemini_api_key()


def test_define_reexports_same_runtime_state_objects():
    assert define.xp_setting is runtime_state.xp_setting
    assert define.gpt_chat_threads is runtime_state.gpt_chat_threads
    assert define.anti_raid_settings_cache is runtime_state.anti_raid_settings_cache
    assert define.last_auto_respond_time is runtime_state.last_auto_respond_time


def test_bot_factory_keeps_phase1_contract():
    intents = build_intents()
    assert intents.presences is False

    allowed_mentions = build_allowed_mentions()
    bot = build_bot(intents=intents, allowed_mentions=allowed_mentions)

    assert isinstance(bot, type(define.bot))
    assert bot.cooldowns == {}
    assert isinstance(bot.allowed_mentions, discord.AllowedMentions)
    assert bot.allowed_mentions.everyone is False
    assert bot.allowed_mentions.users is True
    assert bot.allowed_mentions.roles is True
    assert bot.allowed_mentions.replied_user is True


def test_lazy_gemini_client_defers_key_validation_until_access():
    client = LazyGeminiClient(api_key=None)

    with pytest.raises(ValueError, match="No API key was provided"):
        _ = client.models


def test_commands_define_imports_without_gemini_key(tmp_path):
    script = f"""
import sys
sys.path.insert(0, {str(Path(__file__).resolve().parents[2])!r})
from commands import define
print(type(define.bot).__name__)
"""
    env = os.environ.copy()
    env.pop("GEMENI_API_KEY", None)

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Bot" in result.stdout
