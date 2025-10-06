"""
GarlicBot Phrase Commands

문구 관리 관련 명령어들입니다.
"""

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import is_blocked
from services.database_service import add_phrase, get_phrase, get_phrase_by_name, remove_phrase
from utils.constants import developer


class PhraseCog(commands.Cog):
    """문구 관리 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)

    async def phrase_autocomplete(self, interaction: discord.Interaction, current: str):
        """문구 이름 자동완성"""
        try:
            # 사용자가 접근 가능한 문구들을 가져옵니다
            phrases = []

            # 개인 문구
            user_phrases = await get_phrase_by_name(current, interaction.user.id, interaction.guild.id, interaction.user.guild_permissions.ban_members)
            if user_phrases:
                if isinstance(user_phrases, list):
                    phrases.extend(user_phrases)
                else:
                    phrases.append(user_phrases)

            # 서버 문구들 가져오기 (간단한 구현)
            # 실제로는 더 복잡한 로직이 필요할 수 있습니다

            # 최대 25개로 제한
            choices = []
            for phrase in phrases[:25]:
                if isinstance(phrase, dict) and 'name' in phrase:
                    choices.append(app_commands.Choice(name=phrase['name'], value=str(phrase.get('id', phrase['name']))))

            return choices

        except Exception as e:
            self.logger.error(f"Phrase autocomplete error: {e}")
            return []

    @app_commands.command(name="문구추가", description="문구를 추가합니다.")
    @app_commands.describe(
        문구이름="추가할 문구 이름",
        문구내용="추가할 문구 내용",
        사용권한="권한 설정"
    )
    @app_commands.choices(
        사용권한=[
            app_commands.Choice(name="개인 (본인만 사용이 가능하도록 설정)", value="user"),
            app_commands.Choice(name="서버 유저 (해당 서버의 모든 유저가 사용이 가능하도록 설정)", value="server_all"),
            app_commands.Choice(name="서버 관리자 (해당 서버에서 멤버 차단하기 권한을 가진 관리자만 사용이 가능하도록 설정)", value="server_admin")
        ]
    )
    async def add_phrase(self, interaction: discord.Interaction, 문구이름: str, 문구내용: str, 사용권한: str):
        """문구를 추가합니다."""
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

        # 권한 확인
        if (사용권한 == "server_all" or 사용권한 == "server_admin") and not interaction.user.guild_permissions.manage_guild:
            embed = discord.Embed(
                title="권한 부족",
                description="권한이 부족합니다. 다음 권한이 필요합니다: `서버 관리하기`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # 길이 제한 확인
        if len(문구내용) > 2000:
            embed = discord.Embed(
                title="오류",
                description="문구 내용이 2000자를 초과합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        if len(문구이름) > 70:
            embed = discord.Embed(
                title="오류",
                description="문구 이름이 70자를 초과합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # 줄바꿈 처리
        문구내용 = 문구내용.replace("\\n", "\n")

        try:
            # 데이터베이스에 추가
            if 사용권한 == "user":
                await add_phrase(문구이름, 사용권한, None, interaction.user.id, 문구내용)
            elif 사용권한 in ["server_all", "server_admin"]:
                await add_phrase(문구이름, 사용권한, interaction.guild.id, None, 문구내용)
            else:
                embed = discord.Embed(
                    title="오류",
                    description="잘못된 사용권한 값입니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            embed = discord.Embed(
                title="완료",
                description=f"`{문구이름}` 문구가 추가되었습니다.",
                color=int("a5f0ff", 16)
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Add phrase error: {e}")
            embed = discord.Embed(
                title="오류",
                description="문구 추가 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="문구제거", description="문구를 제거합니다.")
    @app_commands.describe(문구이름="제거할 문구 이름")
    async def remove_phrase_cmd(self, interaction: discord.Interaction, 문구이름: str):
        """문구를 제거합니다."""
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

        try:
            # 문구 ID로 변환 시도
            try:
                문구이름 = int(문구이름)
            except:
                pass

            # 문구 조회
            phrase = None
            if isinstance(문구이름, int):
                phrase = await get_phrase(문구이름)
            else:
                phrase = await get_phrase_by_name(문구이름, interaction.user.id, interaction.guild.id, interaction.user.guild_permissions.ban_members)

            if not phrase:
                embed = discord.Embed(
                    title="오류",
                    description="해당 문구가 존재하지 않습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # 권한 확인
            if phrase["type"] == "user" and phrase["user_id"] != interaction.user.id:
                embed = discord.Embed(
                    title="오류",
                    description="해당 문구가 존재하지 않습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            if (phrase["type"] in ["server_all", "server_admin"]) and phrase["server_id"] != interaction.guild.id:
                embed = discord.Embed(
                    title="오류",
                    description="해당 문구가 존재하지 않습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            if (phrase["type"] in ["server_admin", "server_all"]) and not interaction.user.guild_permissions.manage_guild:
                embed = discord.Embed(
                    title="권한 부족",
                    description="권한이 부족합니다. 다음 권한이 필요합니다: `서버 관리하기`",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # 문구 제거
            await remove_phrase(phrase["id"])

            embed = discord.Embed(
                title="완료",
                description="문구가 제거되었습니다.",
                color=int("a5f0ff", 16)
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Remove phrase error: {e}")
            embed = discord.Embed(
                title="오류",
                description="문구 제거 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="문구출력", description="문구를 출력합니다.")
    @app_commands.describe(
        문구이름="출력할 문구 이름",
        개인응답="개인응답 여부"
    )
    async def print_phrase(self, interaction: discord.Interaction, 문구이름: str, 개인응답: bool = False):
        """문구를 출력합니다."""
        if not 개인응답:
            await interaction.response.defer()
        else:
            await interaction.response.defer(ephemeral=True)

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

        try:
            # 문구 조회
            phrase = None
            try:
                phrase_id = int(문구이름)
                phrase = await get_phrase(phrase_id)
            except:
                pass

            if not phrase:
                phrase = await get_phrase_by_name(
                    문구이름,
                    interaction.user.id,
                    interaction.guild.id,
                    interaction.user.guild_permissions.ban_members,
                )

            if not phrase:
                embed = discord.Embed(
                    title="오류",
                    description="해당 문구가 존재하지 않습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # 권한 확인
            if phrase["type"] == "user" and phrase["user_id"] != interaction.user.id:
                embed = discord.Embed(
                    title="오류",
                    description="해당 문구가 존재하지 않습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            if (phrase["type"] in ["server_all", "server_admin"]) and phrase["server_id"] != interaction.guild.id:
                embed = discord.Embed(
                    title="오류",
                    description="해당 문구가 존재하지 않습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            if phrase["type"] == "server_admin" and not interaction.user.guild_permissions.ban_members:
                embed = discord.Embed(
                    title="권한 부족",
                    description="권한이 부족합니다. 다음 권한이 필요합니다: `멤버 차단하기`",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # 초대 링크 확인
            if ("discord.com/invite/" in phrase["phrase"] or
                "discord://-/invite/" in phrase["phrase"] or
                "discord.gg/" in phrase["phrase"]) and not 개인응답:
                embed = discord.Embed(
                    title="오류",
                    description="문구에 디스코드 서버 초대 링크가 포함되어 있습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # 줄바꿈 처리
            phrase_content = phrase["phrase"].replace("\\n", "\n")

            embed = discord.Embed(
                title=f"{phrase['name']}",
                description=phrase_content,
                color=int("a5f0ff", 16)
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Print phrase error: {e}")
            embed = discord.Embed(
                title="오류",
                description="문구 출력 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(PhraseCog(bot))