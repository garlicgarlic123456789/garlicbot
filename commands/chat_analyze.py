import discord
from discord import app_commands
from discord import *
from commands.define import *
from commands.database import *

class chat_analyze(app_commands.Group) : 
    def __init__(self):
        super().__init__(name="채팅분석", description="채팅분석 관련 명령어")
    
    @app_commands.command(name="기능설정", description="채팅분석을 위한 기능을 활성화 또는 비활성화합니다.")
    @app_commands.describe(사용여부 = "기능 활성화 여부")
    @app_commands.choices(
        사용여부=[
            app_commands.Choice(name="활성화", value="활성화"),
            app_commands.Choice(name="비활성화", value="비활성화"),
        ]
    )
    @app_commands.default_permissions(administrator=True)
    async def chat_analyze_onoff(self, interaction: discord.Interaction, 사용여부: str, 내용동의여부: bool = False):
        await interaction.response.defer()
        if 사용여부 == "활성화" : onoff = True
        else : onoff = False

        if onoff and not 내용동의여부 : 
            embed = discord.Embed(
                title = "알림",
                description = "채팅분석 기능이 활성화되지 않았습니다. 아래 내용을 확인하신 후에, 내용에 동의하시는 경우 `/채팅분석 기능설정` 명령어에서 `내용동의여부` 값을 `True`로 설정하시면 기능 활성화가 가능합니다.\n\n> 채팅분석 기능은 아직 개발 중에 있으며, 현재는 채팅분석을 위한 채팅 데이터 수집 부분만 개발이 완료되었습니다. 따라서 현재는 채팅분석 기능을 활성화하더라도 기능을 사용할 수 없습니다. 다만, 지금 채팅분석 기능을 미리 활성화해두시는 경우 추후 채팅분석 기능이 정식으로 출시됐을 때, 더 많은 채팅 데이터를 기반으로 더 자세한 분석을 받아보실 수는 있습니다.\n\n> 채팅분석 기능을 활성화하는 경우, 활성화한 기간 동안 서버에서 일어나는 채팅 관련 데이터를 봇이 켜져있는 동안 자동으로 수집합니다. 수집하는 데이터는 다음과 같습니다: \n> \n> 1. 서버의 시간별(분 단위) 채팅 메시지 건수 및 채팅을 전송한 유저 수\n> 2. 채널의 시간별(분 단위) 채팅 메시지 건수 및 채팅을 전송한 유저 수",
                color = discord.Color.yellow()
            )
            await interaction.followup.send(embed = embed)
            return

        try : 
            await update_chat_analyze_onoff(interaction.guild.id, onoff)
        except Exception as e : 
            global error
            print(f"오류 #{error}: {e}")
            embed = discord.Embed(
                title="오류",
                description=f"오류 #{error}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            error += 1
            return

        if onoff : 
            embed = discord.Embed(
                title = "완료",
                description = "채팅분석 기능이 활성화되었습니다.\n\n이제 채팅을 기반으로 한 채팅분석 결과를 확인하실 수 있습니다.",
                color = int("a5f0ff", 16)
            )
        else : 
            embed = discord.Embed(
                title = "완료",
                description = "채팅분석 기능이 비활성화되었습니다.\n\n더 이상 채팅 분석을 위한 데이터를 수집하지 않습니다.",
                color = int("a5f0ff", 16)
            )

        await interaction.followup.send(embed = embed)
        return