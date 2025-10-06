"""
GarlicBot AI Commands

AI 관련 명령어들입니다.
"""

import discord
from discord import app_commands
from discord.ext import commands
import google.generativeai as genai
import asyncio
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import requests
import datetime
import holidays
from discord.ui import View, Button
from youtube_transcript_api import YouTubeTranscriptApi

from config import permissions
from utils.helpers import format_timestamp
from utils.message_utils import fetch_messages
from utils.helpers import is_blocked
from utils.constants import fast_transfer, developer, train_timetable_api_key, train_arrivals_api_key
from config.models import two_five_lite_model


class AICommands(commands.Cog):
    """AI 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)

        # Gemini API 초기화
        genai.configure(api_key=self.bot.config.get('GEMINI_API_KEY', ''))

    async def collect_message(self, interaction, start_message_link, end_message_link):
        """메시지 링크에서 메시지들을 수집합니다."""
        start_message_channel = start_message_link.split("/")[-2]
        if end_message_link is not None:
            end_message_channel = end_message_link.split("/")[-2]
            if start_message_channel != end_message_channel:
                return [False, "different_channel"]

        start_message_id = start_message_link.split("/")[-1]
        if end_message_link is not None:
            end_message_id = end_message_link.split("/")[-1]
        else:
            end_message_id = None

        channel = self.bot.get_channel(int(start_message_channel))
        if not channel:
            return [False, "invalid_channel"]

        messages = []
        if end_message_id is not None:
            async for message in channel.history(
                limit=None,
                after=discord.Object(int(start_message_id), type=discord.Message),
                before=discord.Object(int(end_message_id), type=discord.Message),
                oldest_first=True
            ):
                messages.append(f"{message.author.display_name}: {message.content}")
        else:
            async for message in channel.history(
                limit=None,
                after=discord.Object(int(start_message_id), type=discord.Message),
                oldest_first=True
            ):
                messages.append(f"{message.author.display_name}: {message.content}")

        if not messages:
            return [False, "no_message"]
        return [True, messages]

    async def get_channel_list(self, guild):
        """서버의 채널 목록을 가져옵니다."""
        channels = []
        for channel in guild.channels:
            if isinstance(channel, (discord.CategoryChannel, discord.TextChannel, discord.VoiceChannel, discord.ForumChannel)):
                # 채널 타입 문자열 변환
                if isinstance(channel, discord.CategoryChannel):
                    type_str = "카테고리"
                elif isinstance(channel, discord.TextChannel):
                    type_str = "텍스트"
                elif isinstance(channel, discord.VoiceChannel):
                    type_str = "음성"
                elif isinstance(channel, discord.ForumChannel):
                    type_str = "포럼"
                else:
                    continue

                channels.append(f"{channel.name} ({type_str})")

        if channels:
            return [True, channels]
        else:
            return [False, "no_channel"]

    @app_commands.command(name="서버조언", description="서버 관련 조언을 AI에게 구합니다.")
    @app_commands.describe(
        시작메시지="조언의 기반이 될 메시지 범위의 시작점 링크",
        끝메시지="조언의 기반이 될 메시지 범위의 끝점 링크 (선택)",
        채널정보제공="채널 목록 정보를 AI에게 제공할지 여부",
        메시지제공="메시지 기록을 AI에게 제공할지 여부",
        프롬프트="AI에게 할 질문이나 요청사항"
    )
    async def server_advice(
        self,
        interaction: discord.Interaction,
        시작메시지: str,
        프롬프트: str,
        끝메시지: str = None,
        채널정보제공: bool = True,
        메시지제공: bool = True
    ):
        """서버 관련 조언을 AI에게 구합니다."""

        await interaction.response.defer()

        # 차단 사용자 확인
        status, until, reason = is_blocked(interaction.user)
        if status:
            embed = discord.Embed(
                title="사용 제한",
                description=f"AI 조언을 사용할 수 없는 환경입니다.\n\n**사유:** {reason}\n**해제 시각:** {until}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # 서버 확인
        if not interaction.guild:
            embed = discord.Embed(
                title="오류",
                description="이 명령어는 서버에서만 사용할 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # 메시지 수집
        if 메시지제공:
            if not 시작메시지:
                embed = discord.Embed(
                    title="오류",
                    description="메시지 제공을 선택하셨다면 시작 메시지 링크를 필수로 입력해야 합니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            messages = await self.collect_message(interaction, 시작메시지, 끝메시지)
            if not messages[0]:
                embed = discord.Embed(
                    title="오류",
                    description={
                        "different_channel": "시작 메시지와 끝 메시지가 같은 채널에 있어야 합니다.",
                        "invalid_channel": "유효하지 않은 채널입니다.",
                        "no_message": "지정된 범위에 메시지가 없습니다."
                    }.get(messages[1], messages[1]),
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            else:
                messages = messages[1]
        else:
            messages = ["*(제공되지 않음)*"]

        # 채널 정보 수집
        if 채널정보제공:
            channels = await self.get_channel_list(interaction.guild)
            if channels[0]:
                channels = channels[1]
            else:
                embed = discord.Embed(
                    title="오류",
                    description="채널 정보를 가져올 수 없습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
        else:
            channels = ["*(제공되지 않음)*"]

        # 사용자 역할 정보
        user_roles = [role.name for role in interaction.user.roles if not role.is_default()]
        role_info = ", ".join(user_roles) if user_roles else "일반 사용자"

        try:
            # Gemini API 호출
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = await asyncio.to_thread(
                model.generate_content,
                f"""
                이름이 '{interaction.guild.name}'인 디스코드 서버에서 아래와 같은 유저가 서버에 관해 조언을 구하고 있습니다.

                유저 이름: {interaction.user.display_name} ({interaction.user.name})
                유저의 역할: {role_info}
                하려는 조언(유저의 프롬프트): {프롬프트}

                서버의 메시지 기록 중 일부: {messages}
                서버의 채널 구성: {channels}

                위 정보를 참고하여 해당 유저에게 조언을 해주세요. 조언은 최대 3000자 이내여야 합니다.
                """
            )

            response_text = response.text
            if len(response_text) > 4000:
                response_text = response_text[:4000] + "\n\n(AI 조언이 4000자를 초과하여 이하 생략)"

            embed = discord.Embed(
                title="🤖 AI 서버 조언",
                description=f"**요청자:** {interaction.user.mention}\n\n{response_text}",
                color=int("a5f0ff", 16)
            )

            embed.set_footer(text=f"{format_timestamp(interaction.created_at)}")

            await interaction.followup.send(embed=embed)

            self.logger.info(f"AI advice requested by {interaction.user}: {프롬프트[:50]}...")

        except Exception as e:
            self.logger.error(f"AI advice error: {e}")
            embed = discord.Embed(
                title="오류",
                description="AI 조언 생성 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    # 요약 명령어 그룹
    summarize_group = app_commands.Group(name="요약", description="요약 관련 명령어")

    @summarize_group.command(name="대화", description="특정 메시지 범위에 해당되는 메시지들을 요약합니다.")
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
    async def summarize_message(
        self,
        interaction: discord.Interaction,
        시작: str,
        끝: str = None,
        프롬프트: str = "이 대화를 한국어로 요약해 주세요.",
        개인응답: str = "False"
    ):
        """특정 메시지 범위에 해당되는 메시지들을 요약합니다."""

        if 개인응답 == "False":
            await interaction.response.defer()
        else:
            await interaction.response.defer(ephemeral=True)

        # 차단 사용자 확인
        status, until, reason = is_blocked(interaction.user)
        if status:
            embed = discord.Embed(
                title="사용 제한",
                description=f"요약을 사용할 수 없는 환경입니다.\n\n**사유:** {reason}\n**해제 시각:** {until}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # 쿨다운 확인
        user_id = interaction.user.id
        current_time = time.time()

        if user_id not in self.bot.cooldowns:
            self.bot.cooldowns[user_id] = 0

        if current_time - self.bot.cooldowns[user_id] < 1 * 60:  # 60초 = 1분
            embed = discord.Embed(
                title="쿨다운 중",
                description="이 명령어는 1분마다 한 번 사용 가능합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # owner_id 역할 확인 및 쿨다운 설정
        if user_id == developer:
            self.bot.cooldowns[user_id] = current_time

        # 입력 검증
        if "discord.gg/" in 프롬프트 or "discord.com/invite/" in 프롬프트:
            embed = discord.Embed(
                title="입력 오류",
                description="프롬프트에 초대 링크를 포함할 수 없습니다.",
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

            # 채널 가져오기 및 검증
            channel = self.bot.get_channel(start_channel_id)
            if not channel:
                embed = discord.Embed(
                    title="채널 오류",
                    description="시작 메시지의 채널을 찾을 수 없습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            if channel.id != interaction.channel.id:
                embed = discord.Embed(
                    title="권한 오류",
                    description="메시지가 있는 채널에서만 요약할 수 있습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # 메시지 불러오기
            messages = await fetch_messages(channel, start_message_id, end_message_id)
            if not messages:
                embed = discord.Embed(
                    title="메시지 오류",
                    description="지정된 범위에 요약할 메시지가 없습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # 메시지 내용을 합치기
            text_to_summarize = "\n\n".join(f"{msg.author.display_name}: {msg.content}" for msg in reversed(messages))
            text_to_summarize += f"\n\n{프롬프트}"

            # Gemini API 호출
            response = two_five_lite_model.generate_content(text_to_summarize)

            # 응답 전송
            embed = discord.Embed(
                title="📝 대화 요약",
                description=f"**[경고!]** AI는 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n**Gemini 2.0 Flash**의 답변:\n\n{response.text}",
                color=int("a5f0ff", 16)
            )

            embed.set_footer(text=f"{format_timestamp(interaction.created_at)}")

            await interaction.followup.send(embed=embed)

            self.logger.info(f"Message summarized by {interaction.user}: {len(messages)} messages")

        except discord.Forbidden:
            embed = discord.Embed(
                title="권한 부족",
                description="봇에게 메시지 기록을 읽을 권한이 부족합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Summarize message error: {e}")
            embed = discord.Embed(
                title="오류",
                description="대화 요약 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @summarize_group.command(name="유튜브", description="특정 링크에 해당되는 유튜브 영상을 요약합니다.")
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
    async def summarize_youtube(
        self,
        interaction: discord.Interaction,
        링크: str,
        프롬프트: str = "이 대화를 한국어로 요약해 주세요.",
        개인응답: str = "False"
    ):
        """특정 링크에 해당되는 유튜브 영상을 요약합니다."""

        if 개인응답 == "False":
            await interaction.response.defer()
        else:
            await interaction.response.defer(ephemeral=True)

        # 차단 사용자 확인
        status, until, reason = is_blocked(interaction.user)
        if status:
            embed = discord.Embed(
                title="사용 제한",
                description=f"유튜브 요약을 사용할 수 없는 환경입니다.\n\n**사유:** {reason}\n**해제 시각:** {until}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # 개발자 권한 확인
        if interaction.user.id != developer:
            embed = discord.Embed(
                title="권한 부족",
                description="이 기능은 개발자만 사용할 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        try:
            # 유튜브 URL에서 비디오 ID 추출
            video_id = self.extract_video_id(링크)
            if not video_id:
                embed = discord.Embed(
                    title="URL 오류",
                    description="유효한 유튜브 URL을 입력해주세요.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # 자막 가져오기
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
            except Exception as e:
                embed = discord.Embed(
                    title="자막 오류",
                    description="이 영상의 자막을 가져올 수 없습니다. 자막이 없는 영상일 수 있습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # 자막 텍스트 합치기
            transcript_text = ""
            for entry in transcript:
                transcript_text += entry['text'] + " "

            # 텍스트가 너무 긴 경우 자르기
            if len(transcript_text) > 10000:
                transcript_text = transcript_text[:10000] + "..."

            # Gemini API 호출
            response = two_five_lite_model.generate_content(f"{프롬프트}\n\n영상 자막 내용:\n{transcript_text}")

            # 응답 전송
            embed = discord.Embed(
                title="� 유튜브 영상 요약",
                description=f"**[경고!]** AI는 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n**Gemini 2.0 Flash**의 답변:\n\n{response.text}",
                color=int("a5f0ff", 16)
            )

            embed.set_footer(text=f"{format_timestamp(interaction.created_at)}")

            await interaction.followup.send(embed=embed)

            self.logger.info(f"YouTube video summarized by {interaction.user}: {video_id}")

        except Exception as e:
            self.logger.error(f"YouTube summarize error: {e}")
            embed = discord.Embed(
                title="오류",
                description="유튜브 요약 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    def extract_video_id(self, url):
        """유튜브 URL에서 비디오 ID를 추출합니다."""
        import re

        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    # 철도 명령어 그룹
    train_group = app_commands.Group(name="철도", description="철도 관련 명령어")

    @train_group.command(name="빠른환승", description="수도권 전철 빠른 환승 정보를 확인합니다.")
    @app_commands.describe(
        노선="정보를 확인할 노선",
        역="정보를 확인할 역 (뒤에 '역' 자 제외)"
    )
    async def fast_transfer(
        self,
        interaction: discord.Interaction,
        노선: str,
        역: str
    ):
        """수도권 전철 빠른 환승 정보를 확인합니다."""

        await interaction.response.defer()

        # 차단 사용자 확인
        status, until, reason = is_blocked(interaction.user)
        if status:
            embed = discord.Embed(
                title="사용 제한",
                description=f"철도 정보를 사용할 수 없는 환경입니다.\n\n**사유:** {reason}\n**해제 시각:** {until}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # 역 이름 처리
        if 역 == "총신대입구":
            역 = "이수"
        역 += "역"

        try:
            transfer_info = fast_transfer[노선]
        except KeyError:
            embed = discord.Embed(
                title="노선 오류",
                description="등록되지 않은 노선이거나 노선명이 유효하지 않습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        try:
            embed = discord.Embed(
                title=f"🚇 {역} 빠른 환승 정보",
                description=f"**{노선}**\n\n{transfer_info[역]}",
                color=int("a5f0ff", 16)
            )

            embed.set_footer(text=f"{format_timestamp(interaction.created_at)}")

            await interaction.followup.send(embed=embed)

        except KeyError:
            embed = discord.Embed(
                title="역 정보 없음",
                description=f"{역}의 환승 정보를 찾을 수 없습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Fast transfer error: {e}")
            embed = discord.Embed(
                title="오류",
                description="빠른 환승 정보 조회 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @train_group.command(name="도착정보", description="수도권 전철 역의 전철 도착 정보를 확인합니다.")
    @app_commands.describe(
        역명="역명 (뒤에 '역' 자 제외)",
        열차종류="확인할 열차의 종류 (선택)",
        행선지="확인할 열차의 행선지 (선택)"
    )
    @app_commands.choices(
        열차종류=[
            app_commands.Choice(name="전체", value="전체"),
            app_commands.Choice(name="특급", value="특급"),
            app_commands.Choice(name="급행", value="급행"),
            app_commands.Choice(name="일반", value="일반")
        ]
    )
    async def subway_arrival(
        self,
        interaction: discord.Interaction,
        역명: str,
        열차종류: str = None,
        행선지: str = None
    ):
        """수도권 전철 역의 전철 도착 정보를 확인합니다."""

        await interaction.response.defer()

        # 차단 사용자 확인
        status, until, reason = is_blocked(interaction.user)
        if status:
            embed = discord.Embed(
                title="사용 제한",
                description=f"도착 정보를 사용할 수 없는 환경입니다.\n\n**사유:** {reason}\n**해제 시각:** {until}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        if 열차종류 == "전체":
            열차종류 = None

        실제입력역명 = 역명

        # 역명 변환 로직
        station_name_map = {
            "평택지제": "지제",
            "총신대입구": "총신대입구(이수)",
            "이수": "총신대입구(이수)",
            "이수(총신대입구)": "총신대입구(이수)",
            "응암": "응암순환(상선)",
            "공릉": "공릉(서울산업대입구)",
            "남한산성입구": "남한산성입구(성남법원, 검찰청)",
            "대모산입구": "대모산",
            "천호": "천호(풍납토성)",
            "몽촌토성": "몽촌토성(평화의문)",
            "쌍용": "쌍용(나사렛대)",
            "신정": "신정(은행정)",
            "오목교": "오목교(목동운동장앞)",
            "군자": "군자(능동)",
            "아차산": "아차산(어린이대공원후문)",
            "광나루": "광나루(장신대)",
            "굽은다리": "굽은다리(강동구민회관앞)",
            "올림픽공원": "올림픽공원(한국체대)",
            "새절": "새절(신사)",
            "증산": "증산(명지대앞)",
            "월드컵경기장": "월드컵경기장(성산)",
            "대흥": "대흥(서강대앞)",
            "안암": "안암(고대병원앞)",
            "월곡": "월곡(동덕여대)",
            "상월곡": "상월곡(한국과학기술연구원)",
            "화랑대": "화랑대(서울여대입구)",
            "어린이대공원": "어린이대공원(세종대)",
            "숭실대입구": "숭실대입구(살피재)",
            "상도": "상도(중앙대앞)",
        }

        역명 = station_name_map.get(역명, 역명)

        # 신촌역 구분 로직
        if "신촌" in 역명:
            if "경의" in 역명 or "민자" in 역명 or "지상" in 역명:
                역명 = "신촌(경의중앙선)"
            elif "지하" in 역명 or "2" in 역명:
                역명 = "신촌"
            else:
                embed = discord.Embed(
                    title="역 구분 필요",
                    description="경의선 신촌역과 2호선 신촌역을 구분하여 입력해주세요.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

        try:
            data = self.get_subway_info(역명)
            arrivals = data["realtimeArrivalList"]

        except Exception as e:
            self.logger.error(f"Subway info API error: {e}")
            embed = discord.Embed(
                title="API 오류",
                description="지하철 도착 정보를 가져오는 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # 도착 정보 처리
        subway_info = {}
        for arrival in arrivals:
            if 열차종류 is not None and arrival["btrainSttus"] != 열차종류:
                continue
            if 행선지 != None and arrival["bstatnNm"] != 행선지:
                continue

            # 노선 ID를 이름으로 변환
            line_map = {
                "1001": "1호선", "1002": "2호선", "1003": "3호선", "1004": "4호선", "1005": "5호선",
                "1006": "6호선", "1007": "7호선", "1008": "8호선", "1063": "경의중앙선", "1065": "공항철도",
                "1077": "신분당선", "1075": "수인분당선", "1081": "경강선", "1067": "경춘선", "1092": "우이신설선",
                "1009": "9호선", "1093": "서해선", "1032": "GTX-A", "1094": "신림선"
            }
            line = line_map.get(arrival["subwayId"], arrival["subwayId"])

            direction = arrival["updnLine"]  # 상행/하행
            arrival_info = arrival["arvlMsg2"]

            # 도착 정보 파싱
            match = re.search(r"\[(\d+)\]번째 전역 \((.*?)\)", arrival_info)
            if match:
                number = int(match.group(1))
                content = match.group(2)
                # 역명 변환
                station_convert = {
                    "지제": "평택지제",
                    "총신대입구": "이수",
                    "이수(총신대입구)": "이수",
                    "총신대입구(이수)": "이수"
                }
                content = station_convert.get(content, content)

                if number == 2:
                    arrival_info = f"전전역 ({content})"
                else:
                    arrival_info = f"{number}전역 ({content})"
            elif arrival_info == f"{역명} 도착":
                arrival_info = "당역 도착"
            elif arrival_info == f"{역명} 진입":
                arrival_info = "당역 진입"
            elif arrival_info == f"{역명} 출발":
                arrival_info = "당역 출발"

            train_info = {
                "열차번호": arrival["btrainNo"],
                "행선지": arrival["bstatnNm"] + " (" + arrival["btrainSttus"] + ")",
                "도착 정보": arrival_info,
                "도착 예정": f"약 {int(arrival['barvlDt']) // 60} 분 {int(arrival['barvlDt']) % 60}초 후"
            }

            if line not in subway_info:
                subway_info[line] = {}

            if direction not in subway_info[line]:
                subway_info[line][direction] = []

            subway_info[line][direction].append(train_info)

        # 결과 출력
        text = f"{실제입력역명}역의 지하철 도착 정보입니다. 참고용으로만 사용하시기 바랍니다.\n"

        if len(subway_info) == 0:
            text += "\n도착 정보가 비어 있습니다."
        else:
            for line, directions in subway_info.items():
                text += f"\n**{line} 도착 정보**\n"
                for direction, trains in directions.items():
                    text += f"- **{direction}**\n"
                    for train in trains:
                        text += f"  - 열차번호: {train['열차번호']}, 행선지: {train['행선지']}, 현재 위치: {train['도착 정보']}, 도착 예정: {train['도착 예정']}\n"

        embed = discord.Embed(
            title=f"🚇 {실제입력역명}역 지하철 도착 정보",
            description=text,
            color=int("a5f0ff", 16)
        )

        embed.set_footer(text=f"{format_timestamp(interaction.created_at)}")

        await interaction.followup.send(embed=embed)

    @train_group.command(name="정보", description="열차번호를 입력하고 열차에 대한 정보를 확인합니다.")
    @app_commands.describe(
        열차번호="머리 글자 및 열차 번호",
        상하행="열차의 방향",
        날짜="해당 열차의 날짜 (입력 형식: YYYYMMDD, 선택)",
        개인응답="개인응답 사용 여부 (선택)"
    )
    @app_commands.choices(
        상하행=[
            app_commands.Choice(name="상행", value="상행"),
            app_commands.Choice(name="하행", value="하행"),
            app_commands.Choice(name="외선순환 (2호선)", value="외선"),
            app_commands.Choice(name="내선순환 (2호선)", value="내선")
        ]
    )
    async def train_info(
        self,
        interaction: discord.Interaction,
        열차번호: str,
        상하행: str,
        날짜: str = None,
        개인응답: bool = False
    ):
        """열차번호를 입력하고 열차에 대한 정보를 확인합니다."""

        await interaction.response.defer(ephemeral=개인응답)

        # 차단 사용자 확인
        status, until, reason = is_blocked(interaction.user)
        if status:
            embed = discord.Embed(
                title="사용 제한",
                description=f"열차 정보를 사용할 수 없는 환경입니다.\n\n**사유:** {reason}\n**해제 시각:** {until}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        if not 날짜:
            날짜 = self.get_today_date()

        try:
            # 실시간 정보 가져오기
            위치, 지연 = await self.get_train_info_railblue(열차번호, 날짜)

            # 시간표 정보 가져오기
            timetable_result = await self.get_train_timetable(열차번호, 날짜, 상하행)

            embed2 = discord.Embed(
                title=f"열차 #{열차번호} 실시간 정보",
                description=f"**[주의!]** 이 정보는 참고용으로만 사용하시기 바랍니다.\n\n- 위치: {위치}\n- 지연: {지연}",
                color=int("a5f0ff", 16),
            )
            embed2.set_footer(text=f"정보 업데이트 시각: {self.get_current_time()}")

            if not timetable_result[0]:
                embed = discord.Embed(
                    title=f"열차 #{열차번호} 시각표 정보",
                    description="**[주의!]** 이 정보는 시각표를 기준으로 한 정보입니다. 실제 도착 시각과 차이가 있을 수 있습니다.\n\n시각표 정보를 조회할 수 없었습니다. 지원되지 않는 노선이거나 열차 번호가 올바르지 않을 수 있습니다.",
                    color=int("a5f0ff", 16)
                )
                await interaction.followup.send(embeds=[embed, embed2])
                return

            # 페이지 생성 및 전송
            pages = self.generate_timetable_pages(열차번호, timetable_result[2])
            view = self.TrainTimetablePaginator(pages, embed2)
            await interaction.followup.send(embeds=[pages[0], embed2], view=view)

            self.logger.info(f"Train info requested by {interaction.user}: {열차번호}")

        except Exception as e:
            self.logger.error(f"Train info error: {e}")
            embed = discord.Embed(
                title="오류",
                description="열차 정보 조회 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    def get_today_date(self):
        """오늘 날짜를 YYYYMMDD 형식으로 반환합니다."""
        return datetime.datetime.now().strftime("%Y%m%d")

    def get_current_time(self):
        """현재 시각을 반환합니다."""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async def get_train_info_railblue(self, train, date):
        """RailBlue에서 열차 실시간 정보를 가져옵니다."""
        try:
            options = webdriver.FirefoxOptions()
            options.add_argument("--headless")
            driver = webdriver.Firefox(options=options)
            driver.get(f"https://rail.blue/railroad/logis/Default.aspx?company=&train={train}&date={date}#!")
            await asyncio.sleep(2.5)

            train_info = driver.find_element(by=By.ID, value="spDrive")
            parsed_info = await self.parse_train_info(train_info.text)

            driver.quit()

            if parsed_info is None:
                return "*(알 수 없음)*", "*(알 수 없음)*"

            if parsed_info[0]:  # 이동 중
                loc_msg = f"{parsed_info[1]} → {parsed_info[2]}"
                if parsed_info[3]:  # 지연 정보 있음
                    if parsed_info[4] >= 0:
                        delay_msg = f"지연 {parsed_info[4]}분 {parsed_info[5]}초"
                    else:
                        delay_msg = f"조기 {-parsed_info[4]}분 {-parsed_info[5]}초"
                else:
                    delay_msg = "정시 운행"
            else:  # 정차 중
                loc_msg = f"{parsed_info[1]}역 정차 중"
                if parsed_info[2]:  # 지연 정보 있음
                    if parsed_info[3] >= 0:
                        delay_msg = f"지연 {parsed_info[3]}분 {parsed_info[4]}초"
                    else:
                        delay_msg = f"조기 {-parsed_info[3]}분 {-parsed_info[4]}초"
                else:
                    delay_msg = "정시 운행"

            return loc_msg, delay_msg

        except Exception as e:
            self.logger.error(f"RailBlue API error: {e}")
            return "*(알 수 없음)*", "*(알 수 없음)*"

    async def parse_train_info(self, text):
        """RailBlue에서 가져온 텍스트를 파싱합니다."""
        # 운행 종료 확인
        if "운행 종료" in text:
            return [False, "종착역", False]

        # 정차 중 확인
        match = re.search(r"(\w+역)\s*정차\s*중", text)
        if match:
            station = match.group(1)
            # 지연 정보 확인
            delay_match = re.search(r"지연\s*(\d+)분\s*(\d+)초", text)
            if delay_match:
                minutes = int(delay_match.group(1))
                seconds = int(delay_match.group(2))
                return [False, station, True, minutes, seconds]
            return [False, station, False]

        # 이동 중 확인
        match = re.search(r"(\w+역)\s*→\s*(\w+역)", text)
        if match:
            from_station = match.group(1)
            to_station = match.group(2)
            # 지연 정보 확인
            delay_match = re.search(r"지연\s*(\d+)분\s*(\d+)초", text)
            if delay_match:
                minutes = int(delay_match.group(1))
                seconds = int(delay_match.group(2))
                return [True, from_station, to_station, True, minutes, seconds]
            return [True, from_station, to_station, False]

        return None

    async def get_train_timetable(self, trainnum, date, updown):
        """열차 시간표 정보를 가져옵니다."""
        try:
            # 주말 구분
            date_obj = datetime.datetime.strptime(date, "%Y%m%d")
            if date_obj.weekday() >= 5:  # 토요일(5) 또는 일요일(6)
                weekend = "S"
            else:
                # 공휴일 확인
                kr_holidays = holidays.KR()
                if date in kr_holidays:
                    weekend = "H"
                else:
                    weekend = "W"

            # 노선 결정 로직 (단순화)
            if trainnum.startswith("1") or trainnum.startswith("K"):
                line = "경부선"
            elif trainnum.startswith("3"):
                line = "경의선"
            else:
                line = "경부선"  # 기본값

            # 시간 (현재 시각 사용)
            time = datetime.datetime.now().strftime("%H%M")

            url = f"http://apis.data.go.kr/B553766/schedule/getTrainSch?dataType=JSON&serviceKey={train_timetable_api_key}&numOfRows=100&tmprTmtblYn=N&upbdnbSe={updown}&wkndSe={weekend}&lineNm={line}&searchDt={time}&trainno={trainnum}"

            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            if data.get("response", {}).get("body", {}).get("items") == "":
                return [False, "No data"]

            items = data["response"]["body"]["items"]["item"]
            if not isinstance(items, list):
                items = [items]

            timetable = {}
            for item in items:
                station = item["stnm"]
                stop_type = "정차" if item["stopyn"] == "Y" else "통과"
                arrive_time = item.get("arvTm", "-")
                depart_time = item.get("dptTm", "-")

                timetable[station] = {
                    "stop": stop_type,
                    "arrivetime": arrive_time,
                    "departtime": depart_time
                }

            return [True, "Success", timetable]

        except Exception as e:
            self.logger.error(f"Timetable API error: {e}")
            return [False, str(e)]

    def generate_timetable_pages(self, train, data):
        """시간표 페이지를 생성합니다."""
        items = list(data.items())
        pages = []
        items_per_page = 5

        for i in range(0, len(items), items_per_page):
            chunk = items[i:i + items_per_page]

            embed = discord.Embed(
                title=f"열차 #{train} 시각표 정보",
                description="**[주의!]** 이 정보는 시각표를 기준으로 한 정보입니다. 실제 도착 시각과 차이가 있을 수 있습니다.",
                color=int("a5f0ff", 16)
            )

            for station, info in chunk:
                stop_type = info['stop']
                arrive_time = info['arrivetime']
                depart_time = info['departtime']

                title = f"{station}역 ({stop_type})"
                if stop_type == "정차":
                    description = f"- 도착 시각: {arrive_time}\n- 출발 시각: {depart_time}"
                elif stop_type == "출발":
                    description = f"- 출발 시각: {depart_time}"
                else:
                    description = f"- 통과"

                embed.add_field(name=title, value=description, inline=False)

            pages.append(embed)

        return pages

    class TrainTimetablePaginator(View):
        """열차 시간표 페이지네이터"""

        def __init__(self, pages, real_time_embed):
            super().__init__(timeout=300)
            self.pages = pages
            self.current_page = 0
            self.real_time_embed = real_time_embed
            self.update_buttons()

        def update_buttons(self):
            self.previous_button.disabled = self.current_page == 0
            self.next_button.disabled = self.current_page == len(self.pages) - 1

        @discord.ui.button(label="이전", style=discord.ButtonStyle.primary)
        async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page > 0:
                self.current_page -= 1
                self.update_buttons()
                await interaction.response.edit_message(embeds=[self.pages[self.current_page], self.real_time_embed], view=self)

        @discord.ui.button(label="다음", style=discord.ButtonStyle.primary)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page < len(self.pages) - 1:
                self.current_page += 1
                self.update_buttons()
                await interaction.response.edit_message(embeds=[self.pages[self.current_page], self.real_time_embed], view=self)


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(AICommands(bot))