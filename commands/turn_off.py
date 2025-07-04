import discord

from discord import app_commands
import sys
from discord.ext import commands

from commands.define import *

def setup(bot):
    @bot.tree.command(name = "종료", description = "봇을 종료합니다.")
    @app_commands.describe(
        방식="봇 종료 방식",
    )
    @app_commands.choices(방식=[
        app_commands.Choice(name="bot.close()", value="bot.close()"),
        app_commands.Choice(name="sys.exit(0)", value="sys.exit(0)"),
        app_commands.Choice(name="sys.exit(1)", value="sys.exit(1)"),
    ])
    async def turn_off(interaction: discord.Interaction, 방식: str = "bot.close()") :
        if interaction.user.id != developer :
            embed = discord.Embed(
                title="오류",
                description="명령어 사용 권한이 부족합니다. 개발자(이)여야 합니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        embed = discord.Embed(
            title="완료",
            description="곧 봇이 종료됩니다...",
            color=int("a5f0ff", 16)
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)

        if 방식 == "bot.close()" :
            await bot.close()
        elif 방식 == "sys.exit(0)":
            sys.exit(0)
        elif 방식 == "sys.exit(1)":
            sys.exit(1)