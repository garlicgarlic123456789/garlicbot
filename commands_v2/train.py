"""
GarlicBot Train Commands

철도 관련 명령어들입니다.
"""

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import is_blocked
from utils.constants import fast_transfer


class TrainCog(commands.Cog):
    """철도 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)
        self.error_count = 0  # 오류 카운터

    @app_commands.command(name="빠른환승", description="수도권 전철 빠른 환승 정보를 확인합니다.")
    @app_commands.describe(
        노선="정보를 확인할 노선을 입력해 주세요.",
        역="정보를 확인할 역을 입력해 주세요. (뒤에 '역' 자 제외)"
    )
    async def fast_transfer_command(self, interaction: discord.Interaction, 노선: str, 역: str):
        """수도권 전철 빠른 환승 정보를 확인합니다."""
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

        # 역명 변환
        if 역 == "총신대입구":
            역 = "이수"

        역 += "역"

        try:
            transfer_info = fast_transfer[노선]
        except KeyError:
            embed = discord.Embed(
                title="오류",
                description="노선 정보를 가져오는 도중 오류가 발생했습니다.\n등록되지 않은 노선이거나 노선명이 유효하지 않은 경우 일반적으로 이 오류가 표시됩니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        try:
            result_text = f"{역}의 빠른 환승 정보는 다음과 같습니다:\n\n{transfer_info[역]}"

            embed = discord.Embed(
                title="🚆 빠른 환승 정보",
                description=result_text,
                color=int("a5f0ff", 16)
            )
            embed.set_footer(text=f"요청자: {interaction.user.display_name}")

            await interaction.followup.send(embed=embed)

            # 로그 기록
            self.logger.info(f"Fast transfer info requested by {interaction.user.name}({interaction.user.id}): {노선} {역}")

        except KeyError:
            global error
            embed = discord.Embed(
                title="오류",
                description=f"해당 역의 환승 정보를 찾을 수 없습니다.\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            self.error_count += 1
        except Exception as e:
            self.logger.error(f"Fast transfer error: {e}")
            embed = discord.Embed(
                title="오류",
                description=f"오류 #{self.error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            self.error_count += 1


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(TrainCog(bot))