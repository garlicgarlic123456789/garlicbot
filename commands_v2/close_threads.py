"""
GarlicBot Thread Commands

스레드 관리 관련 명령어들입니다.
"""

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import is_blocked


class ThreadCog(commands.Cog):
    """스레드 관리 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)

    @app_commands.command(name="스레드일괄처리", description="해당 채널의 모든 스레드를 닫거나 잠금 처리(또는 둘 모두)합니다.")
    @app_commands.choices(
        잠금처리=[
            app_commands.Choice(name="True", value="True"),
            app_commands.Choice(name="False", value="False")
        ],
        닫기처리=[
            app_commands.Choice(name="True", value="True"),
            app_commands.Choice(name="False", value="False")
        ]
    )
    @app_commands.describe(
        잠금처리="스레드를 잠금 처리할지 여부",
        닫기처리="스레드를 닫기(아카이브) 처리할지 여부"
    )
    async def close_all_threads(
        self,
        interaction: discord.Interaction,
        잠금처리: str = "False",
        닫기처리: str = "False"
    ):
        """해당 채널의 모든 스레드를 닫거나 잠금 처리합니다."""
        # 서버 확인
        if not interaction.guild:
            embed = discord.Embed(
                title="오류",
                description="이 명령어는 서버에서만 사용할 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # 서버 주인 권한 확인
        if interaction.user.id != interaction.guild.owner_id:
            embed = discord.Embed(
                title="오류",
                description="이 명령어는 서버 주인만 사용할 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

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

        # 파라미터 변환
        lock_threads = 잠금처리 == "True"
        archive_threads = 닫기처리 == "True"

        # 처리할 스레드 수 계산
        processed_count = 0
        locked_count = 0
        archived_count = 0

        try:
            # 채널의 모든 스레드 처리
            for thread in interaction.channel.threads:
                thread_modified = False

                # 아카이브 처리 (닫기)
                if not thread.archived and archive_threads:
                    await thread.edit(
                        archived=True,
                        reason=f"사용자 {interaction.user.id}({interaction.user.name})의 스레드 일괄 처리 명령어 사용"
                    )
                    archived_count += 1
                    thread_modified = True

                # 잠금 처리
                if not thread.locked and lock_threads:
                    await thread.edit(
                        locked=True,
                        reason=f"사용자 {interaction.user.id}({interaction.user.name})의 스레드 일괄 처리 명령어 사용"
                    )
                    locked_count += 1
                    thread_modified = True

                if thread_modified:
                    processed_count += 1

            # 결과 메시지 생성
            if processed_count == 0:
                description = "처리할 스레드가 없거나 이미 모든 스레드가 요청된 상태입니다."
            else:
                actions = []
                if archived_count > 0:
                    actions.append(f"닫기: {archived_count}개")
                if locked_count > 0:
                    actions.append(f"잠금: {locked_count}개")
                description = f"총 {processed_count}개의 스레드를 처리했습니다.\n\n" + "\n".join(actions)

            embed = discord.Embed(
                title="🧵 스레드 일괄 처리 완료",
                description=description,
                color=int("a5f0ff", 16)
            )
            embed.set_footer(text=f"요청자: {interaction.user.display_name}")

            await interaction.followup.send(embed=embed)

            # 로그 기록
            self.logger.info(f"Thread batch processing by {interaction.user.name}({interaction.user.id}): "
                           f"processed={processed_count}, archived={archived_count}, locked={locked_count}")

        except Exception as e:
            self.logger.error(f"Thread batch processing error: {e}")
            embed = discord.Embed(
                title="오류",
                description="스레드 일괄 처리 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(ThreadCog(bot))