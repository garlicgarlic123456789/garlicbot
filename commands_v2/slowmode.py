"""
GarlicBot Slowmode Commands

슬로우모드 관련 명령어들입니다.
"""

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import is_blocked


class SlowmodeCog(commands.Cog):
    """슬로우모드 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)

    @app_commands.command(name="슬로우모드", description="채널의 슬로우모드를 설정합니다.")
    @app_commands.describe(
        시간="슬로우모드 시간 (초 단위, 0-21600)",
        채널="설정할 채널 (기본값: 현재 채널)"
    )
    @app_commands.default_permissions(manage_channels=True)
    async def set_slowmode(
        self,
        interaction: discord.Interaction,
        시간: int,
        채널: discord.TextChannel = None
    ):
        """채널의 슬로우모드를 설정합니다."""
        await interaction.response.defer()

        # 차단 사용자 확인
        status, until, reason = is_blocked(interaction.user)
        if status:
            embed = discord.Embed(
                title="오류",
                description=f"이 기능을 사용할 수 없는 환경입니다.\n\n**사유:** {reason}\n**해제 시각:** {until}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # 시간 검증
        if 시간 < 0:
            embed = discord.Embed(
                title="오류",
                description="슬로우모드 시간이 올바르지 않습니다. 0초 이상의 값을 입력해주세요.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        if 시간 > 60 * 60 * 6:  # 6시간 = 21600초
            embed = discord.Embed(
                title="오류",
                description="슬로우모드 시간이 올바르지 않습니다. 6시간 이하의 값을 입력해주세요.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # 채널 설정
        target_channel = 채널 if 채널 is not None else interaction.channel

        try:
            await target_channel.edit(slowmode_delay=시간)

            embed = discord.Embed(
                title="✅ 슬로우모드 설정 완료",
                description=f"**채널:** {target_channel.mention}\n**슬로우모드:** {시간}초",
                color=int("a5f0ff", 16)
            )
            embed.set_footer(text=f"요청자: {interaction.user.display_name}")

            await interaction.followup.send(embed=embed)

            # 로그 기록
            self.logger.info(f"Slowmode set by {interaction.user.name}({interaction.user.id}): "
                           f"channel={target_channel.name}, delay={시간}s")

        except discord.Forbidden:
            embed = discord.Embed(
                title="오류",
                description="봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `채널 관리하기` 권한이 있는지 확인해 주세요.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Slowmode setting error: {e}")
            embed = discord.Embed(
                title="오류",
                description="슬로우모드 설정 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(SlowmodeCog(bot))