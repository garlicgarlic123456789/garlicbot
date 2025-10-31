"""
GarlicBot Timeout Management Commands

타임아웃 관리 관련 명령어들입니다.
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta

from utils.helpers import is_blocked


class TimeoutCog(commands.Cog):
    """타임아웃 관리 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)

    async def add_timeout(self, user: discord.Member, seconds: int, reason: str = None, ignore_ongoing_timeout_duration: bool = False):
        """사용자에게 타임아웃을 추가합니다."""
        try:
            if ignore_ongoing_timeout_duration:
                new_timeout = discord.utils.utcnow() + timedelta(seconds=seconds)
            else:
                if user.timed_out_until and user.timed_out_until > discord.utils.utcnow():
                    # 기존 타임아웃 시간에 추가
                    new_timeout = user.timed_out_until + timedelta(seconds=seconds)
                else:
                    # 현재 시간에서 타임아웃 시간 계산
                    new_timeout = discord.utils.utcnow() + timedelta(seconds=seconds)

            await user.edit(timed_out_until=new_timeout, reason=reason)
            return True
        except Exception as e:
            self.logger.error(f"Failed to add timeout: {e}")
            return False

    # TODO: 타임아웃 관리 명령어들을 여기에 추가할 수 있습니다.
    # 현재는 유틸리티 함수만 포함되어 있습니다.


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(TimeoutCog(bot))