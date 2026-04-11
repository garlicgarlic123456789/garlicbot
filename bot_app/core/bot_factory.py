import discord
from discord.ext import commands

from bot_app.config.constants import (
    BOT_COMMAND_PREFIX,
    BOT_HEARTBEAT_TIMEOUT,
    BOT_MAX_MESSAGES,
    BOT_SHARD_COUNT,
)


def build_intents() -> discord.Intents:
    intents = discord.Intents.all()
    intents.presences = False
    return intents


def build_bot(
    *,
    intents: discord.Intents,
    allowed_mentions: discord.AllowedMentions,
) -> commands.Bot:
    bot = commands.Bot(
        command_prefix=BOT_COMMAND_PREFIX,
        max_messages=BOT_MAX_MESSAGES,
        intents=intents,
        heartbeat_timeout=BOT_HEARTBEAT_TIMEOUT,
        shard_count=BOT_SHARD_COUNT,
        allowed_mentions=allowed_mentions,
    )
    bot.cooldowns = {}
    return bot
