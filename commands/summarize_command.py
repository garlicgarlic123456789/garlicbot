import discord
import re
from discord import app_commands
from commands.define import *
import requests
import asyncio
import time
from commands.fuction_collect_message import fetch_messages

class summarize_command(app_commands.Group) : 
    def __init__(self):
        super().__init__(name="요약", description="요약 관련 명령어")
    
    @app_commands.command(name="대화", description="특정 메시지 범위에 해당되는 메시지들을 요약합니다.")
    @app_commands.describe(
        시작="요약을 시작할 메시지의 링크",
        끝="요약을 끝낼 메시지의 링크 (선택)",
        프롬프트="요약 프롬프트 (선택)",
        개인응답 = "개인응답 여부 (선택, 기본 값 \'비활성화\')"
    )
    @app_commands.choices(
        개인응답 = [
            app_commands.Choice(name = "활성화", value = "True"),
            app_commands.Choice(name = "비활성화", value = "False"),
        ]
    )
    async def summarize_message(interaction: discord.Interaction, 시작: str, 끝: str = None, 프롬프트: str = "이 대화를 한국어로 요약해 주세요.", 개인응답: str = "False"):
        if 개인응답 == "False" : 
            await interaction.response.defer()
        else :
            await interaction.response.defer(ephemeral=True)

        status, until, reason = is_blocked(interaction.user)
        
        # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
        if status:
            embed = discord.Embed(
                title="오류",
                description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 수 있는 사용자로 설정되어 있지 않습니다. {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return

        user_id = interaction.user.id
        current_time = time.time()

        # 쿨다운 확인
        if user_id not in bot.cooldowns:
            bot.cooldowns[user_id] = 0

        if current_time - bot.cooldowns[user_id] < 1 * 60:  # 60초 = 1분
            embed = discord.Embed(
                title=f"오류", # name
                description=f"이 명령어는 1분마다 한 번 사용 가능합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # owner_id 역할 확인
        if user_id == developer:
            bot.cooldowns[user_id] = current_time

        if "discord.gg/" in 프롬프트 or "discord.com/invite/" in 프롬프트 :
            embed = discord.Embed(
                title="오류",
                description=f"이 모델을 사용할 수 없는 환경입니다.\n\n입력이 올바르지 않습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return

        try:
            # 메시지 링크에서 채널 ID와 메시지 ID 추출
            start_channel_id, start_message_id = map(int, 시작.split("/")[-2:])
            end_channel_id = None
            end_message_id = None

            if 끝:
                end_channel_id, end_message_id = map(int, 끝.split("/")[-2:])

            # 채널 가져오기
            channel = bot.get_channel(start_channel_id)
            if not channel:
                embed = discord.Embed(
                    title=f"오류", # name
                    description=f"channel의 값이 올바르지 않습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            if channel.id != interaction.channel.id:
                embed = discord.Embed(
                    title=f"오류", # name
                    description=f"channel의 값이 올바르지 않습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # 메시지 불러오기
            messages = await fetch_messages(channel, start_message_id, end_message_id)
            if not messages:
                embed = discord.Embed(
                    title=f"오류", # name
                    description=f"messages의 값이 올바르지 않습니다. 이 오류는 지정된 범위의 메시지들의 개수가 0개일 때 표시됩니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # 메시지 내용을 합치기
            text_to_summarize = "\n\n".join(f"{msg.author.display_name}: {msg.content}" for msg in reversed(messages))
            if interaction.user.id == developer : 
                print(text_to_summarize)
            text_to_summarize += f"\n\n{프롬프트}"

            # Gemini API 호출
            response = two_five_lite_model.generate_content(text_to_summarize)

            # 응답 전송
            embed = discord.Embed(
                title="성공",
                description=f"**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\nGemini 2.0 Flash의 답변은 다음과 같습니다: \n\n{response.text}",
                color=int("a5f0ff", 16)
            )
            await interaction.followup.send(embed=embed)
        
        except discord.Forbidden : 
            embed = discord.Embed(
                title="오류",
                description=f"봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `채널 보기` 권한이 있는지 확인해 주세요.\n- 봇에게 `메시지 기록 보기` 권한이 있는지 확인해 주세요.\n- 봇이 해당 채널을 볼 수 있는지 확인해 주세요.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        except Exception as e:
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
    
    @app_commands.command(name="유튜브", description="특정 링크에 해당되는 유튜브 영상을 요약합니다.")
    @app_commands.describe(
        링크="요약할 유튜브 영상의 링크",
        프롬프트="요약 프롬프트 (선택)",
        개인응답 = "개인응답 여부 (선택, 기본 값 \'비활성화\')"
    )
    @app_commands.choices(
        개인응답 = [
            app_commands.Choice(name = "활성화", value = "True"),
            app_commands.Choice(name = "비활성화", value = "False"),
        ]
    )
    async def summarize_youtube(interaction: discord.Interaction, 링크: str, 프롬프트: str = "이 대화를 한국어로 요약해 주세요.", 개인응답: str = "False"):
        if 개인응답 == "False" : 
            await interaction.response.defer()
        else :
            await interaction.response.defer(ephemeral=True)

        status, until, reason = is_blocked(interaction.user)

        if status:
            embed = discord.Embed(
                title="오류",
                description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 수 있는 사용자로 설정되어 있지 않습니다. {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        await interaction.followup.send(f"아직 개발 중입니다.")
        
    
