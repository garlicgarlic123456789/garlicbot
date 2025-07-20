import discord
from discord import app_commands

from commands.define import *

import time

def setup(bot):
    @bot.tree.command(name="핑", description="봇의 지연 시간(ping)을 확인합니다.")
    @app_commands.choices(개발자용 = [app_commands.Choice(name = "활성화", value = "True"), app_commands.Choice(name = "비활성화", value = "False")])
    @app_commands.describe(개발자용 = "사용자 친화적인 설명을 비활성화할지 여부를 선택합니다. 기본값은 \'비활성화\'입니다.")
    async def ping(interaction: discord.Interaction, 개발자용: str = "False"):
        status, until, reason = is_blocked(interaction.user)
        
        # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.response.send_message(msg)
            return
        # Gateway latency (WebSocket ping)
        gateway_latency = round(bot.latency * 1000)

        # REST latency 측정
        start = time.perf_counter()
        await interaction.response.defer(thinking=True)  # 응답 대기
        end = time.perf_counter()
        rest_latency = round((end - start) * 1000)

        # 메시지 전송
        if 개발자용 == "True" : 
            embed = discord.Embed(
                title=f"퐁!", # name
                description=f"- REST: {rest_latency}ms\n- Gateway: {gateway_latency}ms",
                color=int("a5f0ff", 16)
            )
        else :
            if rest_latency > 600 :
                embed = discord.Embed(
                    title=f"퐁!", # name
                    description=f"체감 핑: {rest_latency}ms (핑: {gateway_latency}ms)",
                    color=discord.Color.red()
                )
            elif rest_latency > 450 :
                embed = discord.Embed(
                    title=f"퐁!", # name
                    description=f"체감 핑: {rest_latency}ms (핑: {gateway_latency}ms)",
                    color=discord.Color.yellow()
                )
            else: 
                embed = discord.Embed(
                    title=f"퐁!", # name
                    description=f"체감 핑: {rest_latency}ms (핑: {gateway_latency}ms)",
                    color=int("a5f0ff", 16)
                )
        await interaction.followup.send(embed = embed)