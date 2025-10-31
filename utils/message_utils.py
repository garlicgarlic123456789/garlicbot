"""
GarlicBot Message Utilities

메시지 수집 및 처리 관련 유틸리티 함수들입니다.
"""

import discord
from datetime import datetime, timedelta
import json
import os

from discord.ext import commands
from discord import app_commands
from discord import Interaction
from discord import Member
from discord import Embed
from discord import utils
from discord import TextChannel
from discord import User
from discord import PermissionOverwrite
from discord import Permissions
from discord import Embed
from discord import Colour


async def fetch_messages(channel, start_message_id, end_message_id=None):
    """Fetch messages between start_message_id and end_message_id."""
    start_message = await channel.fetch_message(start_message_id)
    messages = []

    async for message in channel.history(limit=None, after=start_message):
        messages.append(message)
        if end_message_id and message.id == end_message_id:
            break

    messages.sort(key=lambda x: x.created_at, reverse=True)

    return messages


async def load_user_messages(bot, user_id: int, user_id2: int, guild_id: int) -> list[str]:
    messages = []
    messages2 = []

    guild = bot.get_guild(guild_id)
    if guild is None:
        return []  # 길드를 찾지 못하면 빈 리스트 반환

    for channel in guild.text_channels:
        if not channel.permissions_for(guild.me).read_message_history:
            continue  # 봇이 히스토리를 읽을 권한이 없는 경우 건너뜀

        try:
            async for message in channel.history(limit=30000):
                if message.author.id == user_id:
                    messages.append(message.content)
                if message.author.id == user_id2:
                    messages2.append(message.content)

            if len(messages) >= 1000 and len(messages2) >= 1000:
                messages.reverse()
                messages2.reverse()
                return messages[-1000:-1], messages2[-1000:-1]
            elif len(messages) >= 1000 :
                messages.reverse()
                messages2.reverse()
                return messages[-1000:-1], messages2
            elif len(messages2) >= 1000 :
                messages.reverse()
                messages2.reverse()
                return messages, messages2[-1000:-1]
        except (discord.Forbidden, discord.HTTPException):
            continue  # 에러 발생시 해당 채널은 건너뜀

    messages.reverse()
    messages2.reverse()

    return messages, messages2