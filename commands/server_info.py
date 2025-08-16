import discord
from discord import app_commands

from commands.database import *
from commands.define import *
import pytz

kst = pytz.timezone('Asia/Seoul')

def setup(bot) : 
    @bot.tree.command(name="서버정보", description="서버 정보를 확인합니다.")
    async def server_info(interaction: discord.Interaction):
        await interaction.response.defer()
        status, until, reason = is_blocked(interaction.user)
        if status : 
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return
        
        guild = interaction.guild
        embed = discord.Embed(title="서버 정보", color=int("a5f0ff", 16))
        embed.add_field(name="서버 이름", value=guild.name, inline=False)
        embed.add_field(name="서버 ID", value=guild.id, inline=False)
        created_at = guild.created_at.astimezone(kst).strftime("%Y-%m-%d %H:%M:%S")
        embed.add_field(name="서버 생성일", value=created_at, inline=False)
        all_count = guild.member_count
        bot_count = 0
        for i in guild.members : 
            if i.bot : 
                bot_count += 1
        user_count = all_count - bot_count
        embed.add_field(name="서버 인원 수", value=f"- 인원(봇 포함): {all_count}\n- 순인원(봇 제외): {user_count}\n- 도입된 봇 개수: {bot_count}", inline=False)
        embed.add_field(name="부스트 개수", value=guild.premium_subscription_count, inline=False)
        embed.add_field(name="서버 주인", value=guild.owner.mention, inline=False)
        embed.add_field(name="역할 개수", value=f"{len(guild.roles)} / 250", inline=False)
        embed.add_field(name="채널 개수", value=f"{len(guild.channels)} / 500", inline=False)
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        await interaction.followup.send(embed=embed)