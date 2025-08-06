import discord
from discord.ext import commands
from commands.database import *
from commands.define import *

def setup(bot):
    @bot.tree.command(name = "경험치설정", description = "경험치 기능을 설정합니다.")
    @app_commands.default_permissions(administrator = True)
    @app_commands.describe(
        기능사용여부 = "경험치 기능을 켜거나 끕니다.",
        채팅경험치 = "채팅 경험치 양을 설정합니다.",
        채팅경험치쿨다운 = "채팅 경험치 쿨다운을 설정합니다.",
        음성경험치 = "음성 경험치 양을 설정합니다.",
        음성경험치쿨다운 = "음성 경험치 쿨다운을 설정합니다.",
        단위 = "경험치 단위를 설정합니다."
    )
    async def 경험치설정(interaction: discord.Interaction, 기능사용여부: bool, 채팅경험치: int = None, 채팅경험치쿨다운: int = None, 음성경험치: int = None, 음성경험치쿨다운: int = None, 단위: str = None):
        await interaction.response.defer()

        if not interaction.user.guild_permissions.administrator : 
            embed = discord.Embed(
                title = "오류",
                description = "권한이 부족합니다. 다음 권한이 필요합니다: `관리자`",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return

        onoff = 기능사용여부
        chat_xp = 채팅경험치
        chat_xp_cooldown = 채팅경험치쿨다운
        voice_xp = 음성경험치
        voice_xp_cooldown = 음성경험치쿨다운
        unit = 단위

        if onoff and chat_xp is None and voice_xp is None and unit is None and chat_xp_cooldown is None and voice_xp_cooldown is None : 
            embed = discord.Embed(
                title = "오류",
                description = "필수 입력란이 비어 있습니다.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        if not onoff : 
            update_xp_setting(interaction.guild.id, onoff, chat_xp, chat_xp_cooldown, voice_xp, voice_xp_cooldown, unit)
            embed = discord.Embed(
                title = "완료",
                description = "경험치 기능이 비활성화되었습니다.",
                color = int("a5f0ff", 16)
            )
            await interaction.followup.send(embed = embed)
            return
        else : 
            update_xp_setting(interaction.guild.id, onoff, chat_xp, chat_xp_cooldown, voice_xp, voice_xp_cooldown, unit)
            embed = discord.Embed(
                title = "완료",
                description = "경험치 기능이 활성화되었습니다.",
                color = int("a5f0ff", 16)
            )
            await interaction.followup.send(embed = embed)
            return
        