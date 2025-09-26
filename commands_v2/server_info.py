"""
GarlicBot Server Info Commands

서버 정보를 확인하는 명령어들입니다.
"""

import discord
from discord import app_commands
from discord.ext import commands
import pytz

from config import permissions
from utils.helpers import format_timestamp


class ServerInfoCommands(commands.Cog):
    """서버 정보 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)
        self.kst = pytz.timezone('Asia/Seoul')

    @app_commands.command(name="서버정보", description="서버 정보를 확인합니다.")
    async def server_info(self, interaction: discord.Interaction):
        """서버의 상세 정보를 표시합니다."""

        # 권한 확인
        permission_config = permissions.PermissionConfig()
        if not await permission_config.check_user_permission(interaction.user, "server_info"):
            await interaction.response.send_message(
                f"**[오류!]** {interaction.user.mention}님은 이 명령어를 사용할 권한이 없습니다.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        guild = interaction.guild
        if not guild:
            await interaction.followup.send("**[오류!]** 이 명령어는 서버에서만 사용할 수 있습니다.")
            return

        # 서버 정보 수집
        embed = discord.Embed(title="서버 정보", color=int("a5f0ff", 16))

        # 기본 정보
        embed.add_field(name="서버 이름", value=guild.name, inline=False)
        embed.add_field(name="서버 ID", value=f"`{guild.id}`", inline=False)

        # 생성일 (KST)
        created_at = guild.created_at.astimezone(self.kst).strftime("%Y-%m-%d %H:%M:%S")
        embed.add_field(name="서버 생성일", value=created_at, inline=False)

        # 인원 수 통계
        all_count = guild.member_count
        bot_count = sum(1 for member in guild.members if member.bot)
        user_count = all_count - bot_count

        embed.add_field(
            name="서버 인원 수",
            value=f"- 인원(봇 포함): {all_count}\n- 순인원(봇 제외): {user_count}\n- 도입된 봇 개수: {bot_count}",
            inline=False
        )

        # 추가 정보
        embed.add_field(name="부스트 개수", value=guild.premium_subscription_count or 0, inline=False)
        embed.add_field(name="서버 주인", value=guild.owner.mention if guild.owner else "알 수 없음", inline=False)
        embed.add_field(name="역할 개수", value=f"{len(guild.roles)} / 250", inline=False)
        embed.add_field(name="채널 개수", value=f"{len(guild.channels)} / 500", inline=False)

        # 서버 아이콘
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # 푸터
        embed.set_footer(text=f"요청자: {interaction.user} | {format_timestamp(interaction.created_at)}")

        await interaction.followup.send(embed=embed)

        self.logger.info(f"Server info command executed by {interaction.user} for guild {guild.name} ({guild.id})")


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(ServerInfoCommands(bot))