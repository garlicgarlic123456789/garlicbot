from __future__ import annotations

import discord

from bot_app.repositories.settings_repository import settings_repository


def get_automod_setting(server_id: int, repository=settings_repository):
    return repository.get_automod(server_id)


def is_automod_exempt_channel(server_id: int, channel, repository=settings_repository) -> bool:
    if repository.is_automod_exception_channel(server_id, channel.id) is True:
        return True

    if isinstance(channel, discord.Thread):
        if repository.is_automod_exception_channel(server_id, channel.parent.id) is True:
            return True
        if channel.parent.category is not None:
            if repository.is_automod_exception_channel(server_id, channel.parent.category.id) is True:
                return True
        return False

    if channel.category is not None:
        if repository.is_automod_exception_channel(server_id, channel.category.id) is True:
            return True

    return False


def get_block_log_channel_for_guild(bot, server_id: int, repository=settings_repository):
    channel_id = repository.get_block_log_channel(server_id)
    return bot.get_channel(channel_id)
