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
        채팅경험치쿨다운 = "채팅 경험치 쿨다운(단위: 초)을 설정합니다.",
        음성경험치 = "음성 경험치 양을 설정합니다.",
        음성경험치쿨다운 = "음성 경험치 쿨다운(단위: 초)을 설정합니다.",
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

        if onoff and (chat_xp is None or voice_xp is None or chat_xp_cooldown is None or voice_xp_cooldown is None) : 
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
                description = "경험치 기능이 활성화되었습니다.\n\n참고: 아직 음성방 경험치 기능은 개발 중입니다.",
                color = int("a5f0ff", 16)
            )
            await interaction.followup.send(embed = embed)
            return
    
    @bot.tree.command(name = "출석체크설정", description = "출석체크 기능을 설정합니다.")
    @app_commands.default_permissions(administrator = True)
    @app_commands.describe(
        기능사용여부 = "출석체크 기능을 켜거나 끕니다.",
        최소지급경험치 = "출석체크 시 지급할 최소 경험치를 설정합니다.",
        최대지급경험치 = "출석체크 시 지급할 최대 경험치를 설정합니다.",
        지급단위 = "고급 옵션입니다. Random Step 값을 지정할 수 있습니다."
    )
    async def check_set(interaction: discord.Interaction, 기능사용여부: bool, 최소지급경험치: int = None, 최대지급경험치: int = None, 지급단위: int = None):
        await interaction.response.defer()

        if interaction.guild.id in xp_setting : 
            if xp_setting[interaction.guild.id][0] == False : 
                embed = discord.Embed(
                    title = "오류",
                    description = "경험치 기능이 사용 중지되어 있는 서버입니다. 경험치 기능을 먼저 사용 설정해 주세요.",
                    color = discord.Color.red()
                )
                await interaction.followup.send(embed = embed)
                return
        else : 
            temp = get_xp_setting(interaction.guild.id)
            if temp[0] == False : 
                embed = discord.Embed(
                    title = "오류",
                    description = "경험치 기능이 사용 중지되어 있는 서버입니다. 경험치 기능을 먼저 사용 설정해 주세요.",
                    color = discord.Color.red()
                )
                await interaction.followup.send(embed = embed)
                return

        if 최소지급경험치 is None : 
            최소지급경험치 = 0
        if 최대지급경험치 is None : 
            최대지급경험치 = 0
        if 지급단위 is None : 
            지급단위 = 1
        
        if 최소지급경험치 < 0 or 최대지급경험치 < 0 : 
            embed = discord.Embed(
                title = "오류",
                description = "최소 지급 경험치 또는 최대 지급 경험치 값이 0보다 작습니다.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        if 최대지급경험치 < 최소지급경험치 : 
            embed = discord.Embed(
                title = "오류",
                description = "최소 지급 경험치보다 최대 지급 경험치 값이 더 작습니다.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        if 최소지급경험치 > 70000 or 최대지급경험치 > 70000 : 
            embed = discord.Embed(
                title = "오류",
                description = "최소 지급 경험치 또는 최대 지급 경험치 값이 70000보다 큽니다.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        if 지급단위 < 1 : 
            embed = discord.Embed(
                title = "오류",
                description = "고급 옵션에 입력된 값이 올바르지 않습니다.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        if 기능사용여부 : 
            onoff = 1
        else : 
            onoff = 0
        
        await update_attendance_settings(interaction.guild.id, onoff, 최소지급경험치, 최대지급경험치, 지급단위)

        embed = discord.Embed(
            title = "완료",
            description = "출석체크 기능이 설정되었습니다.",
            color = int("a5f0ff", 16)
        )
        await interaction.followup.send(embed = embed)
        return
        