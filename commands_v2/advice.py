"""
GarlicBot AI Advice Commands

AI 조언 관련 명령어들입니다.
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio

from utils.helpers import is_blocked
from utils.message_utils import fetch_messages
from services.ai_service import AIService
from utils.constants import developer


class AIAdviceCog(commands.Cog):
    """AI 조언 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)
        self.ai_service = AIService(bot)

    async def collect_messages_for_advice(self, start_message_link: str, end_message_link: str = None):
        """메시지 링크에서 메시지들을 수집합니다."""
        try:
            start_message_channel = start_message_link.split("/")[-2]
            if end_message_link is not None:
                end_message_channel = end_message_link.split("/")[-2]
                if start_message_channel != end_message_channel:
                    return [False, "different_channel"]

            start_message_id = start_message_link.split("/")[-1]
            end_message_id = end_message_link.split("/")[-1] if end_message_link else None

            channel = self.bot.get_channel(int(start_message_channel))
            if not channel:
                return [False, "invalid_channel"]

            messages = []
            if end_message_id is not None:
                async for message in channel.history(
                    limit=None,
                    after=discord.Object(int(start_message_id)),
                    before=discord.Object(int(end_message_id)),
                    oldest_first=True
                ):
                    messages.append(f"{message.author.display_name}: {message.content}")
            else:
                async for message in channel.history(
                    limit=None,
                    after=discord.Object(int(start_message_id)),
                    oldest_first=True
                ):
                    messages.append(f"{message.author.display_name}: {message.content}")

            if not messages:
                return [False, "no_message"]

            return [True, messages]

        except Exception as e:
            self.logger.error(f"Collect messages for advice error: {e}")
            return [False, "error"]

    async def get_channel_list_for_advice(self, guild: discord.Guild):
        """서버의 채널 목록을 가져옵니다."""
        try:
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

        except Exception as e:
            self.logger.error(f"Get channel list for advice error: {e}")
            return [False, "error"]

    @app_commands.command(name="서버조언", description="서버 관리에 대한 AI 조언을 받습니다.")
    @app_commands.describe(
        프롬프트="받고 싶은 조언 내용",
        시작메시지="참고할 메시지 범위의 시작 (선택)",
        끝메시지="참고할 메시지 범위의 끝 (선택)",
        채널정보포함="서버 채널 정보를 포함할지 여부",
        메시지정보포함="메시지 기록을 포함할지 여부"
    )
    async def server_advice(
        self,
        interaction: discord.Interaction,
        프롬프트: str,
        시작메시지: str = None,
        끝메시지: str = None,
        채널정보포함: bool = True,
        메시지정보포함: bool = True
    ):
        """서버 관리에 대한 AI 조언을 받습니다."""
        await interaction.response.defer()

        # 차단 사용자 확인
        status, until, reason = is_blocked(interaction.user)
        if status:
            embed = discord.Embed(
                title="오류",
                description=f"이 기능을 사용할 수 없는 환경입니다.\n\n**사유:** {reason}\n**해제 시각:** {until}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # 서버 확인
        if not interaction.guild:
            embed = discord.Embed(
                title="오류",
                description="서버에서만 사용할 수 있는 기능입니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        try:
            # 메시지 정보 수집
            messages_info = "*(제공되지 않음)*"
            if 메시지정보포함 and 시작메시지:
                messages_result = await self.collect_messages_for_advice(시작메시지, 끝메시지)
                if not messages_result[0]:
                    embed = discord.Embed(
                        title="오류",
                        description=f"메시지 수집 오류: {messages_result[1]}",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return
                messages_info = messages_result[1]

            # 채널 정보 수집
            channels_info = "*(제공되지 않음)*"
            if 채널정보포함:
                channels_result = await self.get_channel_list_for_advice(interaction.guild)
                if channels_result[0]:
                    channels_info = channels_result[1]
                else:
                    channels_info = "*(채널 정보 수집 실패)*"

            # 사용자 역할 정보
            user_roles = [role.name for role in interaction.user.roles]
            role_info = ", ".join(user_roles) if user_roles else "없음"

            # AI 프롬프트 구성
            advice_prompt = f"""
이름이 '{interaction.guild.name}'인 디스코드 서버에서 아래와 같은 유저가 서버에 관해 조언을 구하고 있습니다.

유저 이름: {interaction.user.display_name} ({interaction.user.name})
유저의 역할: {role_info}
하려는 조언(유저의 프롬프트): {프롬프트}

서버의 메시지 기록 중 일부: {messages_info}
서버의 채널 구성: {channels_info}

위 정보를 참고하여 해당 유저에게 조언을 해주세요. 조언은 최대 3000자 이내여야 합니다.
"""

            # AI 서비스를 통한 조언 생성
            try:
                advice = await self.ai_service.generate_advice(advice_prompt)

                # 응답 길이 제한
                if len(advice) > 4000:
                    advice = advice[:4000] + "\n\n(AI 조언이 4000자를 초과하여 이하 생략)"

                embed = discord.Embed(
                    title="AI 서버 조언",
                    description=f"**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n{advice}",
                    color=int("a5f0ff", 16)
                )
                await interaction.followup.send(embed=embed)

            except Exception as ai_error:
                self.logger.error(f"AI advice generation error: {ai_error}")
                embed = discord.Embed(
                    title="오류",
                    description="AI 조언 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Server advice command error: {e}")
            embed = discord.Embed(
                title="오류",
                description="서버 조언 생성 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(AIAdviceCog(bot))