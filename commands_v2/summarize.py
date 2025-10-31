"""
GarlicBot Summarize Commands

요약 관련 명령어들입니다.
"""

import discord
import re
from discord import app_commands
from discord.ext import commands
import requests
import asyncio
import time
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi

from utils.constants import developer, error
from utils.helpers import format_timestamp
from services.ai_service import AIService
from commands.fuction_collect_message import fetch_messages


class SummarizeCog(commands.Cog):
    """요약 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)
        self.ai_service = AIService(bot)
        self.cooldowns = {}  # 쿨다운 추적용

    @app_commands.command(name="대화요약", description="특정 메시지 범위에 해당되는 메시지들을 요약합니다.")
    @app_commands.describe(
        시작="요약을 시작할 메시지의 링크",
        끝="요약을 끝낼 메시지의 링크 (선택)",
        프롬프트="요약 프롬프트 (선택)",
        개인응답="개인응답 여부 (선택, 기본 값 '비활성화')"
    )
    @app_commands.choices(
        개인응답=[
            app_commands.Choice(name="활성화", value="True"),
            app_commands.Choice(name="비활성화", value="False"),
        ]
    )
    async def summarize_message(self, interaction: discord.Interaction, 시작: str, 끝: str = None,
                               프롬프트: str = "이 대화를 한국어로 요약해 주세요.", 개인응답: str = "False"):
        """특정 메시지 범위에 해당되는 메시지들을 요약합니다."""
        if 개인응답 == "False":
            await interaction.response.defer()
        else:
            await interaction.response.defer(ephemeral=True)

        # 임시: 차단 확인 로직 (나중에 moderation_service로 이동)
        # status, until, reason = await self.moderation_service.is_blocked(interaction.user)
        status = False  # 임시로 차단 해제

        if status:
            embed = discord.Embed(
                title="오류",
                description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 수 있는 사용자로 설정되어 있지 않습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        user_id = interaction.user.id
        current_time = time.time()

        # 쿨다운 확인
        if user_id not in self.cooldowns:
            self.cooldowns[user_id] = 0

        if current_time - self.cooldowns[user_id] < 1 * 60:  # 60초 = 1분
            embed = discord.Embed(
                title="오류",
                description="이 명령어는 1분마다 한 번 사용 가능합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # owner_id 역할 확인 (개발자는 쿨다운 무시)
        if user_id == developer:
            self.cooldowns[user_id] = current_time

        if "discord.gg/" in 프롬프트 or "discord.com/invite/" in 프롬프트:
            embed = discord.Embed(
                title="오류",
                description="이 모델을 사용할 수 없는 환경입니다.\n\n입력이 올바르지 않습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        try:
            # 메시지 링크에서 채널 ID와 메시지 ID 추출
            start_channel_id, start_message_id = map(int, 시작.split("/")[-2:])
            end_channel_id = None
            end_message_id = None

            if 끝:
                end_channel_id, end_message_id = map(int, 끝.split("/")[-2:])

            # 채널 가져오기
            channel = self.bot.get_channel(start_channel_id)
            if not channel:
                embed = discord.Embed(
                    title="오류",
                    description="채널의 값이 올바르지 않습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            if channel.id != interaction.channel.id:
                embed = discord.Embed(
                    title="오류",
                    description="채널의 값이 올바르지 않습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # 메시지 불러오기
            messages = await fetch_messages(channel, start_message_id, end_message_id)
            if not messages:
                embed = discord.Embed(
                    title="오류",
                    description="메시지의 값이 올바르지 않습니다. 이 오류는 지정된 범위의 메시지들의 개수가 0개일 때 표시됩니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # 메시지 내용을 합치기
            text_to_summarize = "\n\n".join(f"{msg.author.display_name}: {msg.content}" for msg in reversed(messages))
            if interaction.user.id == developer:
                print(text_to_summarize)
            text_to_summarize += f"\n\n{프롬프트}"

            # AI 서비스를 통한 요약 생성
            try:
                summary = await self.ai_service.summarize_text(text_to_summarize)

                # 응답 전송
                embed = discord.Embed(
                    title="성공",
                    description=f"**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n{summary}",
                    color=int("a5f0ff", 16)
                )
                await interaction.followup.send(embed=embed)

            except Exception as ai_error:
                self.logger.error(f"AI 요약 중 오류 발생: {ai_error}")
                embed = discord.Embed(
                    title="오류",
                    description="AI 서비스 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)

        except discord.Forbidden:
            embed = discord.Embed(
                title="오류",
                description="봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `채널 보기` 권한이 있는지 확인해 주세요.\n- 봇에게 `메시지 기록 보기` 권한이 있는지 확인해 주세요.\n- 봇이 해당 채널을 볼 수 있는지 확인해 주세요.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        except Exception as e:
            global error
            self.logger.error(f"요약 명령어 오류 #{error}: {e}")
            embed = discord.Embed(
                title="오류",
                description=f"오류 #{error}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            error += 1
            return

    @app_commands.command(name="유튜브요약", description="특정 링크에 해당되는 유튜브 영상을 요약합니다.")
    @app_commands.describe(
        링크="요약할 유튜브 영상의 링크",
        프롬프트="요약 프롬프트 (선택)",
        개인응답="개인응답 여부 (선택, 기본 값 '비활성화')"
    )
    @app_commands.choices(
        개인응답=[
            app_commands.Choice(name="활성화", value="True"),
            app_commands.Choice(name="비활성화", value="False"),
        ]
    )
    async def summarize_youtube(self, interaction: discord.Interaction, 링크: str,
                               프롬프트: str = "이 대화를 한국어로 요약해 주세요.", 개인응답: str = "False"):
        """특정 링크에 해당되는 유튜브 영상을 요약합니다."""
        if 개인응답 == "False":
            await interaction.response.defer()
        else:
            await interaction.response.defer(ephemeral=True)

        # 임시: 차단 확인 로직
        status = False

        if status:
            embed = discord.Embed(
                title="오류",
                description="이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 수 있는 사용자로 설정되어 있지 않습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        if interaction.user.id != developer:
            embed = discord.Embed(
                title="오류",
                description="이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 수 있는 사용자로 설정되어 있지 않습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        else:
            try:
                transcript = await self.get_youtube_subtitle(링크)
                for entry in transcript:
                    print(entry['text'])
                await interaction.followup.send("아직 개발 중입니다.")
                return

            except Exception as e:
                self.logger.error(f"유튜브 요약 중 오류 발생: {e}")
                embed = discord.Embed(
                    title="오류",
                    description="유튜브 자막을 가져오는 중 오류가 발생했습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)

    async def get_youtube_subtitle(self, url: str):
        """유튜브 자막을 가져옵니다."""
        # URL에서 비디오 ID 추출
        import re
        video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
        if not video_id_match:
            raise ValueError("유효하지 않은 유튜브 URL입니다.")

        video_id = video_id_match.group(1)

        # 자막 리스트 확인
        available_transcripts = YouTubeTranscriptApi.list_transcripts(video_id)

        # 한국어 자막 가져오기 (ko)
        try:
            korean_transcript = available_transcripts.find_transcript(['ko'])
            transcript = korean_transcript.fetch()
            return transcript
        except Exception:
            # 한국어 자막이 없으면 영어 자막 시도
            try:
                english_transcript = available_transcripts.find_transcript(['en'])
                transcript = english_transcript.fetch()
                return transcript
            except Exception:
                raise ValueError("자막을 찾을 수 없습니다.")


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(SummarizeCog(bot))