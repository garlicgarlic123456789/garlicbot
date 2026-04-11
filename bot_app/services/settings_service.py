from __future__ import annotations

import discord

from bot_app.repositories.settings_repository import settings_repository
from bot_app.types.readability_contracts import AutomodConfig, AutomodExemptionResult, GuildLogChannelSelection


def get_automod_setting(server_id: int, repository=settings_repository) -> AutomodConfig:
    return repository.get_automod(server_id)


def _exempt_channel_result(*, matched_scope: str, matched_channel_id: int) -> AutomodExemptionResult:
    return AutomodExemptionResult(
        status="exempt",
        matched_scope=matched_scope,
        matched_channel_id=matched_channel_id,
    )


def is_automod_exempt_channel(server_id: int, channel, repository=settings_repository) -> AutomodExemptionResult:
    if repository.is_automod_exception_channel(server_id, channel.id) is True:
        return _exempt_channel_result(matched_scope="channel", matched_channel_id=channel.id)

    if isinstance(channel, discord.Thread):
        if repository.is_automod_exception_channel(server_id, channel.parent.id) is True:
            return _exempt_channel_result(matched_scope="thread_parent", matched_channel_id=channel.parent.id)
        if channel.parent.category is not None:
            if repository.is_automod_exception_channel(server_id, channel.parent.category.id) is True:
                return _exempt_channel_result(matched_scope="thread_parent_category", matched_channel_id=channel.parent.category.id)
        return AutomodExemptionResult(status="not_exempt")

    if channel.category is not None:
        if repository.is_automod_exception_channel(server_id, channel.category.id) is True:
            return _exempt_channel_result(matched_scope="category", matched_channel_id=channel.category.id)

    return AutomodExemptionResult(status="not_exempt")


def get_block_log_channel_for_guild(bot, server_id: int, repository=settings_repository):
    channel_id = repository.get_block_log_channel(server_id)
    return bot.get_channel(channel_id)


def update_guild_log_channels(
    *,
    server_id: int,
    selection: GuildLogChannelSelection,
    repository=settings_repository,
) -> GuildLogChannelSelection:
    repository.update_guild_log_channels(server_id, selection)
    return selection
