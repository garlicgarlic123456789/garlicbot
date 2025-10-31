"""
GarlicBot Ping Commands

봇의 지연 시간(ping)을 확인하는 명령어들입니다.
"""

import discord
from discord import app_commands
from discord.ext import commands
import time

from config import permissions
from utils.helpers import format_timestamp


class PingCommands(commands.Cog):
    """핑 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)

    @app_commands.command(name="핑", description="봇의 지연 시간(ping)을 확인합니다.")
    @app_commands.choices(개발자용=[
        app_commands.Choice(name="활성화", value="True"),
        app_commands.Choice(name="비활성화", value="False")
    ])
    @app_commands.describe(개발자용="사용자 친화적인 설명을 비활성화할지 여부를 선택합니다. 기본값은 '비활성화'입니다.")
    async def ping(self, interaction: discord.Interaction, 개발자용: str = "False"):
        """봇의 핑을 측정하고 표시합니다."""

        # 권한 확인 (기존 차단 상태 확인 로직 대체)
        permission_config = permissions.PermissionConfig()
        if not await permission_config.check_user_permission(interaction.user, "ping"):
            await interaction.response.send_message(
                f"**[오류!]** {interaction.user.mention}님은 이 명령어를 사용할 권한이 없습니다.",
                ephemeral=True
            )
            return

        # Gateway latency (WebSocket ping)
        gateway_latency = round(self.bot.latency * 1000)

        # REST latency 측정
        start = time.perf_counter()
        await interaction.response.defer(thinking=True)  # 응답 대기
        end = time.perf_counter()
        rest_latency = round((end - start) * 1000)

        # 응답 생성
        if 개발자용 == "True":
            embed = discord.Embed(
                title="퐁!",
                description=f"- REST: {rest_latency}ms\n- Gateway: {gateway_latency}ms",
                color=int("a5f0ff", 16)
            )
        else:
            # 체감 핑에 따른 색상 결정
            if rest_latency > 600:
                color = discord.Color.red()
            elif rest_latency > 450:
                color = discord.Color.yellow()
            else:
                color = discord.Color.green()

            embed = discord.Embed(
                title="퐁!",
                description=f"체감 핑: {rest_latency}ms (핑: {gateway_latency}ms)",
                color=color
            )

        # 타임스탬프 추가
        embed.set_footer(text=f"측정 시간: {format_timestamp(interaction.created_at)}")

        await interaction.followup.send(embed=embed)

        self.logger.info(f"Ping command executed by {interaction.user} - REST: {rest_latency}ms, Gateway: {gateway_latency}ms")


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(PingCommands(bot))