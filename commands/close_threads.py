import discord
from discord import app_commands

from commands.define import *

def setup(bot):
    @bot.tree.command(name="스레드일괄처리", description="해당 채널의 모든 스레드를 닫거나 잠금 처리(또는 둘 모두)합니다.")
    @app_commands.choices(잠금처리 = [app_commands.Choice(name = "True", value = "True"), app_commands.Choice(name = "False", value = "False")], 닫기처리 = [app_commands.Choice(name = "True", value = "True"), app_commands.Choice(name = "False", value = "False")])
    async def close_all_threads(interaction: discord.Interaction, 잠금처리: str = "False", 닫기처리: str = "False"):
        if interaction.guild is None:
            await interaction.response.send_message("이 명령어는 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return
        
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("이 명령어는 서버 주인만 사용할 수 있습니다.", ephemeral=True)
            return

        await interaction.response.defer()
        status, until, reason = is_blocked(interaction.user)
        
        # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return

        if 잠금처리 == "True" :
            잠금처리 = True
        else :
            잠금처리 = False

        if 닫기처리 == "True" :
            닫기처리 = True
        else :
            닫기처리 = False
        
        for thread in interaction.channel.threads:
            if not thread.archived and 닫기처리 == True:
                await thread.edit(archived=True, reason = f"사용자 {interaction.user.id}의 /스레드일괄처리 명령어 사용")
            if not thread.locked and 잠금처리 == True :
                await thread.edit(locked=True, reason = f"사용자 {interaction.user.id}의 /스레드일괄처리 명령어 사용")
        
        embed = discord.Embed(title="스레드 처리 완료", description = "스레드가 전부 닫기 또는 잠금 처리되었습니다.", color=int("a5f0ff", 16))
        
        await interaction.followup.send(embed=embed)