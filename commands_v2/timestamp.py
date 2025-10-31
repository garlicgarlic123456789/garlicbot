"""
GarlicBot Timestamp Commands

타임스탬프 변환 명령어들입니다.
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from config import permissions
from utils.helpers import format_timestamp


class TimestampCommands(commands.Cog):
    """타임스탬프 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)

    @app_commands.command(name="타임스탬프", description="날짜 및 시각을 입력하여 타임스탬프를 출력합니다.")
    @app_commands.describe(시각="타임스탬프로 변환할 시각 (YYYY-MM-DD HH:MM:SS)")
    async def timestamp(self, interaction: discord.Interaction, 시각: str):
        """입력된 날짜/시각을 Discord 타임스탬프로 변환합니다."""

        # 권한 확인
        permission_config = permissions.PermissionConfig()
        if not await permission_config.check_user_permission(interaction.user, "timestamp"):
            await interaction.response.send_message(
                f"**[오류!]** {interaction.user.mention}님은 이 명령어를 사용할 권한이 없습니다.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # 입력값 정리
        시각 = 시각.replace("\\", "")

        try:
            # 입력된 시각을 datetime 객체로 변환
            dt = datetime.strptime(시각, "%Y-%m-%d %H:%M:%S")

            # 유닉스 시간으로 변환
            unix_timestamp = int(dt.timestamp())

            # 타임스탬프 출력
            embed = discord.Embed(
                title="타임스탬프 변환 완료",
                description=f"- 입력 시각: {시각}\n- 유닉스 시간: `{unix_timestamp}`\n- 디스코드 문법: `<t:{unix_timestamp}>` (`<t:{unix_timestamp}:R>`)",
                color=int("a5f0ff", 16)
            )

            embed.add_field(
                name="미리보기",
                value=f"<t:{unix_timestamp}>\n<t:{unix_timestamp}:R>",
                inline=False
            )

            embed.set_footer(text=f"요청자: {interaction.user} | {format_timestamp(interaction.created_at)}")

            await interaction.followup.send(embed=embed)

            self.logger.info(f"Timestamp command executed by {interaction.user} - input: {시각}, output: {unix_timestamp}")

        except ValueError as e:
            embed = discord.Embed(
                title="입력 오류",
                description="올바른 형식으로 입력해주세요.\n\n**형식:** `YYYY-MM-DD HH:MM:SS`\n**예시:** `2024-01-01 12:30:45`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

            self.logger.warning(f"Timestamp command failed by {interaction.user} - invalid input: {시각}")


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(TimestampCommands(bot))