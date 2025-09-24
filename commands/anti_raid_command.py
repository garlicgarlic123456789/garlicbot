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
    @bot.tree.command(name = "레이드방지설정", description = "레이드 방지 기능을 설정합니다.")
    @app_commands.choices(
        사용여부 = [
            app_commands.Choice(name = "활성화", value = "True"),
            app_commands.Choice(name = "비활성화", value = "False")
        ],
        조치방법 = [
            app_commands.Choice(name = "서버 주인에게 알림", value = "alert"),
            app_commands.Choice(name = "초대 일시정지 후 서버 주인에게 알림", value = "pause_invite"),
            app_commands.Choice(name = "초대 일시정지 및 관련 계정 격리 후 서버 주인에게 알림", value = "isolate"),
            app_commands.Choice(name = "초대 일시정지 및 관련 계정 28일 타임아웃 후 서버 주인에게 알림", value = "timeout"),
            app_commands.Choice(name = "초대 일시정지 및 관련 계정 차단 후 서버 주인에게 알림", value = "ban"),
        ]
    )
    @app_commands.describe(
        사용여부 = "레이드 방지 기능을 사용할지 여부",
        조치방법 = "레이드가 감지되었을 때 조치할 방법",
        알림채널 = "레이드가 감지되었을 때 이를 알릴 채널", 
        시간범위 = "고급 옵션. 사용법을 정확히 모른다면 비워두세요. | 레이드 감지 시간 범위 (초 단위. 기본값: 180)",
        참가횟수 = "고급 옵션. 사용법을 정확히 모른다면 비워두세요. | \'시간범위\' 값의 시간 내에 이 \'참가횟수\' 값의 횟수를 초과하여 유저가 서버에 참가하면 레이드로 간주합니다. (기본값: 5)"
    )
    @app_commands.default_permissions(administrator = True)
    async def anti_raid_settings(interaction: discord.Integration, 사용여부: str, 조치방법: str = None, 알림채널: discord.TextChannel = None, 시간범위: int = 180, 참가횟수: int = 5) : 
        await interaction.response.defer(ephemeral = True)

        if interaction.user.id != interaction.guild.owner.id : 
            embed = discord.Embed(
                title = "오류",
                description = "이 명령어를 사용할 권한이 없습니다. 다음 권한이 필요합니다: `서버 주인`",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        if 사용여부 == "True" : 
            사용여부 = True
        else : 
            사용여부 = False
        
        if 사용여부 == False : 
            await update_anti_raid_settings(interaction.guild.id, 사용여부, "alert", 0, 시간범위, 참가횟수)
            embed = discord.Embed(
                title = "성공",
                description = "레이드 방지 기능의 옵션을 다음과 같이 설정했습니다. \n\n- 기능 사용 여부: 비활성화",
                color = int("a5f0ff", 16)
            )
            await interaction.followup.send(embed = embed)
            return
        else : 
            if 조치방법 is None or 알림채널 is None : 
                embed = discord.Embed(
                    title = "오류",
                    description = "레이드 방지 기능을 활성화하려면 조치방법 값과 알림채널 값을 필수로 입력해야 합니다.",
                    color = discord.Color.red()
                )
                await interaction.followup.send(embed = embed)
                return
            
            if 시간범위 > 900 or 시간범위 < 30 : 
                embed = discord.Embed(
                    title = "오류",
                    description = "시간범위의 값은 30~900초의 범위에서만 설정 가능합니다.",
                    color = discord.Color.red()
                )
                await interaction.followup.send(embed = embed)
                return
            
            if 참가횟수 > 50 or 시간범위 < 3 : 
                embed = discord.Embed(
                    title = "오류",
                    description = "참가횟수의 값은 3~50회의 범위에서만 설정 가능합니다.",
                    color = discord.Color.red()
                )
                await interaction.followup.send(embed = embed)
                return
            
            await update_anti_raid_settings(interaction.guild.id, 사용여부, 조치방법, 알림채널.id, 시간범위, 참가횟수)

            embed = discord.Embed(
                title = "성공",
                description = f"레이드 방지 기능의 옵션을 다음과 같이 설정했습니다. \n\n- 기능 사용 여부: 활성화\n- 조치 방법: {조치방법}\n- 알림 채널: <#{알림채널.id}>\n- 감지 방법: {시간범위}초 내에 {참가횟수}회 이상의 서버 참가가 발생하면 레이드로 판단",
                color = int("a5f0ff", 16)
            )
            await interaction.followup.send(embed = embed)
            return

