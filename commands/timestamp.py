import discord
from datetime import datetime
from discord import app_commands

from commands.define import *

def setup(bot):
    @bot.tree.command(name = "타임스탬프", description = "날짜 및 시각을 입력하여 타임스탬프를 출력합니다.")
    @app_commands.describe(시각 = "타임스탬프로 변환할 시각 (YYYY-MM-DD HH:MM:SS)")
    async def timestamp(interaction: discord.Interaction, 시각: str):
        await interaction.response.defer()

        status, until, reason = is_blocked(interaction.user)
        if status : 
            await interaction.followup.send(f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다.")
            return
        
        시각 = 시각.replace("\\", "")

        try:
            # 입력된 시각을 datetime 객체로 변환
            timestamp = datetime.strptime(시각, "%Y-%m-%d %H:%M:%S")
            
            # 유닉스 시간으로 변환
            timestamp = int(timestamp.timestamp())
            
            # 타임스탬프 출력
            embed = discord.Embed(
                title="완료",
                description=f"- 유닉스 시간: {timestamp}\n- 디스코드 문법: <t:{timestamp}> (<t:{timestamp}:R>)",
                color=int("a5f0ff", 16)
            )
            await interaction.followup.send(embed=embed)
        except ValueError:
            embed = discord.Embed(
                title="오류",
                description=f"입력값이 올바르지 않습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)