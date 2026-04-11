import discord

from discord.ext import commands
from discord import app_commands
from discord import Interaction
from discord import Member
from discord import Embed
from discord import AuditLogAction
from discord import AuditLogDiff
from discord import *

from datetime import datetime
from pytz import timezone

from commands.define import *
from commands.database import *


def setup(bot: commands.Bot):
    @bot.tree.command(name="제재내역수동삭제", description = "개발 명령")
    async def 제재내역수동삭제(interaction: discord.Interaction, id: int):
        if interaction.user.id != developer :
            embed = discord.Embed(
                title="오류",
                description="권한이 부족합니다. 다음 권한이 필요합니다: `개발자`",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
            return
        await interaction.response.defer()
        remove_blockhistory(id)
        await interaction.followup.send(f"제재 내역 #{id} 삭제되었습니다.")
        return

    # add_blockhistory(user_id, admin_id, reason, blocktype, addinfo)
    @bot.tree.command(name="제재내역수동추가", description="개발 명령")
    @app_commands.describe(추가정보="경고의 경우, 경고 개수. 타임아웃의 경우 타임아웃 기간 (초)")
    async def 제재내역수동추가(interaction: discord.Interaction, 유저: discord.User, 관리자: discord.User, 사유: str, 종류: str, 추가정보: int) :
        if interaction.user.id != developer :
            embed = discord.Embed(
                title="오류",
                description="권한이 부족합니다. 다음 권한이 필요합니다: `개발자`",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
            return
        await interaction.response.defer(ephemeral=True)
        add_blockhistory(유저.id, 관리자.id, 사유, 종류, 추가정보, interaction.guild.id)
        embed = discord.Embed(
            title="완료",
            description="처리되었습니다.",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return