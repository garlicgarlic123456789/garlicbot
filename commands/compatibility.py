import discord

from discord.ext import commands
from discord import app_commands
from discord import *

from commands.define import *


def setup(bot: commands.Bot):
    @bot.tree.command(name = "궁합", description = "두 사람이나 항목 간의 궁합을 확인합니다.")
    @app_commands.describe(항목1 = "항목 1 (또는 사람 1)", 항목2 = "항목 2 (또는 사람 2)")
    async def compatibility_function(interaction: discord.Interaction, 항목1: str, 항목2: str) :
        await interaction.response.defer()

        status, until, reason = is_blocked(interaction.user)

        if status : 
            await message.reply(f"**[오류!]** {message.author.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다.", mention_author=False)
            return
        
        compatibility_tuple = tuple(sorted([항목1, 항목2]))

        compatibility_combined = compatibility_tuple[1] + compatibility_tuple[0]

        compatibility_result = hash(compatibility_combined) % 101

        embed = discord.Embed(
            title = "궁합 측정 결과",
            color = int("a5f0ff", 16)
        )

        embed.add_field(name = "측정 대상", value = f"{항목1} ↔ {항목2}")
        embed.add_field(name = "측정 결과", value = f"{compatibility_result}%")

        await interaction.followup.send(embed = embed)