import discord
from discord.ext import commands

from commands.define import *

def setup(bot) : 
    @bot.tree.command(name="슬로우모드", description="채널의 슬로우모드를 설정합니다.")
    @app_commands.default_permissions(manage_channels=True)
    async def set_slowmode(interaction: discord.Interaction, 시간: int, 채널: discord.TextChannel = None):
        await interaction.response.defer()

        if 시간 < 0 : 
            embed = discord.Embed(
                title="오류",
                description="슬로우모드 시간이 올바르지 않습니다. 0초 이상의 값을 입력해주세요.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        if 시간 > 60 * 60 * 6 : 
            embed = discord.Embed(
                title="오류",
                description="슬로우모드 시간이 올바르지 않습니다. 6시간 이하의 값을 입력해주세요.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        if 채널 is None : 
            채널 = interaction.channel

        try : 
            await 채널.edit(slowmode_delay=시간)
        except discord.Forbidden : 
            embed = discord.Embed(
                title="오류",
                description="봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `채널 관리하기` 권한이 있는지 확인해 주세요.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="성공",
            description=f"채널의 슬로우모드가 성공적으로 설정되었습니다.",
            color=int("a5f0ff", 16)
        )
        await interaction.followup.send(embed=embed)
        return
