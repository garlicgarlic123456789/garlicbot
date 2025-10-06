"""
GarlicBot Role Commands

역할 관리 관련 명령어들입니다.
"""

import discord
from discord import app_commands
from discord.ext import commands

from config import permissions
from utils.helpers import format_timestamp
from services.database_service import add_autorole, remove_autorole, get_autorole


class RoleCommands(commands.Cog):
    """역할 관리 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)

    def is_blocked(self, user: discord.User) -> tuple[bool, str, str]:
        """사용자가 차단되었는지 확인합니다."""
        # TODO: 차단 사용자 데이터 로드 로직 구현
        return False, None, None

    @app_commands.command(name="모든역할회수", description="특정 사용자의 모든 역할을 회수합니다.")
    @app_commands.describe(사용자="역할을 회수할 사용자")
    @app_commands.default_permissions(manage_roles=True)
    async def remove_all_roles(
        self,
        interaction: discord.Interaction,
        사용자: discord.Member
    ):
        """특정 사용자의 모든 역할을 회수합니다."""

        # 권한 확인
        permission_config = permissions.PermissionConfig()
        if not await permission_config.check_user_permission(interaction.user, "manage_roles"):
            embed = discord.Embed(
                title="권한 부족",
                description="역할을 관리할 권한이 없습니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # 역할 우선순위 확인
        if 사용자.top_role >= interaction.user.top_role:
            embed = discord.Embed(
                title="권한 부족",
                description="역할 회수 대상의 최상위 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer()

        try:
            # 역할 제거 (@everyone 역할 제외)
            roles_to_remove = [role for role in 사용자.roles if not role.is_default()]
            removed_roles = []

            for role in roles_to_remove:
                try:
                    await 사용자.remove_roles(role)
                    removed_roles.append(role)
                except discord.Forbidden:
                    continue

            if not removed_roles:
                embed = discord.Embed(
                    title="역할 회수 완료",
                    description=f"{사용자.mention}님에게서 회수할 수 있는 역할이 없습니다.",
                    color=int("a5f0ff", 16)
                )
            else:
                embed = discord.Embed(
                    title="역할 회수 완료",
                    description=f"{사용자.mention}님의 모든 역할을 회수했습니다.",
                    color=int("a5f0ff", 16)
                )

                role_list = "\n".join([f"• {role.mention}" for role in removed_roles])
                embed.add_field(
                    name=f"회수된 역할 ({len(removed_roles)}개)",
                    value=role_list,
                    inline=False
                )

            embed.add_field(
                name="실행자",
                value=interaction.user.mention,
                inline=True
            )

            embed.set_footer(text=f"{format_timestamp(interaction.created_at)}")

            await interaction.followup.send(embed=embed)

            self.logger.info(f"All roles removed from {사용자} by {interaction.user}: {len(removed_roles)} roles")

        except discord.Forbidden:
            embed = discord.Embed(
                title="권한 부족",
                description="봇에게 역할 관리 권한이 부족합니다.\n\n**필요한 권한:** `역할 관리하기`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Remove all roles command error: {e}")
            embed = discord.Embed(
                title="오류",
                description="역할 회수 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="역할부여", description="사용자에게 역할을 부여합니다.")
    @app_commands.describe(
        사용자="역할을 부여할 사용자",
        역할="부여할 역할"
    )
    @app_commands.default_permissions(manage_roles=True)
    async def add_role(
        self,
        interaction: discord.Interaction,
        사용자: discord.Member,
        역할: discord.Role
    ):
        """사용자에게 역할을 부여합니다."""

        # 권한 확인
        permission_config = permissions.PermissionConfig()
        if not await permission_config.check_user_permission(interaction.user, "manage_roles"):
            embed = discord.Embed(
                title="권한 부족",
                description="역할을 관리할 권한이 없습니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # 역할 우선순위 확인
        if 역할.position >= interaction.user.top_role.position and interaction.user.id != interaction.guild.owner_id:
            embed = discord.Embed(
                title="권한 부족",
                description=f"{역할.mention} 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer()

        try:
            # 이미 역할이 있는지 확인
            if 역할 in 사용자.roles:
                embed = discord.Embed(
                    title="오류",
                    description=f"{사용자.mention}님은 이미 {역할.mention} 역할을 가지고 있습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            await 사용자.add_roles(역할)

            embed = discord.Embed(
                title="역할 부여 완료",
                description=f"{사용자.mention}님에게 {역할.mention} 역할을 부여했습니다.",
                color=int("a5f0ff", 16)
            )

            embed.add_field(name="부여된 역할", value=역할.mention, inline=True)
            embed.add_field(name="실행자", value=interaction.user.mention, inline=True)

            embed.set_footer(text=f"{format_timestamp(interaction.created_at)}")

            await interaction.followup.send(embed=embed)

            self.logger.info(f"Role {역할.name} added to {사용자} by {interaction.user}")

        except discord.Forbidden:
            embed = discord.Embed(
                title="권한 부족",
                description="봇에게 역할 관리 권한이 부족합니다.\n\n**필요한 권한:** `역할 관리하기`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Add role command error: {e}")
            embed = discord.Embed(
                title="오류",
                description="역할 부여 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="역할회수", description="사용자로부터 역할을 회수합니다.")
    @app_commands.describe(
        사용자="역할을 회수할 사용자",
        역할="회수할 역할"
    )
    @app_commands.default_permissions(manage_roles=True)
    async def remove_role(
        self,
        interaction: discord.Interaction,
        사용자: discord.Member,
        역할: discord.Role
    ):
        """사용자로부터 역할을 회수합니다."""

        # 권한 확인
        permission_config = permissions.PermissionConfig()
        if not await permission_config.check_user_permission(interaction.user, "manage_roles"):
            embed = discord.Embed(
                title="권한 부족",
                description="역할을 관리할 권한이 없습니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # 역할 우선순위 확인
        if 역할.position >= interaction.user.top_role.position and interaction.user.id != interaction.guild.owner_id:
            embed = discord.Embed(
                title="권한 부족",
                description=f"{역할.mention} 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer()

        try:
            # 역할이 있는지 확인
            if 역할 not in 사용자.roles:
                embed = discord.Embed(
                    title="오류",
                    description=f"{사용자.mention}님은 {역할.mention} 역할을 가지고 있지 않습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            await 사용자.remove_roles(역할)

            embed = discord.Embed(
                title="역할 회수 완료",
                description=f"{사용자.mention}님으로부터 {역할.mention} 역할을 회수했습니다.",
                color=int("a5f0ff", 16)
            )

            embed.add_field(name="회수된 역할", value=역할.mention, inline=True)
            embed.add_field(name="실행자", value=interaction.user.mention, inline=True)

            embed.set_footer(text=f"{format_timestamp(interaction.created_at)}")

            await interaction.followup.send(embed=embed)

            self.logger.info(f"Role {역할.name} removed from {사용자} by {interaction.user}")

        except discord.Forbidden:
            embed = discord.Embed(
                title="권한 부족",
                description="봇에게 역할 관리 권한이 부족합니다.\n\n**필요한 권한:** `역할 관리하기`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Remove role command error: {e}")
            embed = discord.Embed(
                title="오류",
                description="역할 회수 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    # Autorole 명령어 그룹
    autorole_group = app_commands.Group(name="자동역할", description="자동 역할 부여 설정을 관리합니다.")

    @autorole_group.command(name="추가", description="자동 역할 부여 설정을 추가합니다.")
    @app_commands.describe(
        역할="자동으로 부여할 역할",
        유형="부여 대상 유형 (all: 모든 사용자, user: 일반 사용자만, bot: 봇만)"
    )
    @app_commands.choices(유형=[
        app_commands.Choice(name="모든 사용자", value="all"),
        app_commands.Choice(name="일반 사용자만", value="user"),
        app_commands.Choice(name="봇만", value="bot")
    ])
    @app_commands.default_permissions(manage_roles=True)
    async def add_autorole(
        self,
        interaction: discord.Interaction,
        역할: discord.Role,
        유형: str
    ):
        """자동 역할 부여 설정을 추가합니다."""

        # 권한 확인
        permission_config = permissions.PermissionConfig()
        if not await permission_config.check_user_permission(interaction.user, "manage_roles"):
            embed = discord.Embed(
                title="권한 부족",
                description="역할을 관리할 권한이 없습니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer()

        try:
            # 현재 자동 역할 설정 개수 확인
            autoroles = await get_autorole(interaction.guild.id)
            if len(autoroles) >= 10:
                embed = discord.Embed(
                    title="설정 제한 초과",
                    description="자동 역할 설정은 최대 10개까지 가능합니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # 자동 역할 추가
            result = await add_autorole(interaction.guild.id, 역할.id, 유형)

            if result[0]:  # 성공
                embed = discord.Embed(
                    title="자동 역할 설정 추가 완료",
                    description=f"{역할.mention} 역할이 자동으로 부여되도록 설정했습니다.",
                    color=int("a5f0ff", 16)
                )

                # 유형 설명
                type_desc = {
                    "all": "모든 사용자",
                    "user": "일반 사용자",
                    "bot": "봇"
                }

                embed.add_field(
                    name="부여 대상",
                    value=f"서버에 참가하는 {type_desc.get(유형, 유형)}",
                    inline=True
                )
                embed.add_field(name="역할", value=역할.mention, inline=True)
                embed.add_field(name="실행자", value=interaction.user.mention, inline=True)

                embed.set_footer(text=f"{format_timestamp(interaction.created_at)}")

                await interaction.followup.send(embed=embed)

                self.logger.info(f"Autorole added: {역할.name} for {유형} by {interaction.user}")

            else:  # 실패
                if result[1] == "autorole_already_exists":
                    embed = discord.Embed(
                        title="설정 중복",
                        description=f"{역할.mention} 역할은 이미 자동 역할 설정에 등록되어 있습니다.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                else:
                    embed = discord.Embed(
                        title="오류",
                        description="자동 역할 설정 추가 중 오류가 발생했습니다.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Add autorole command error: {e}")
            embed = discord.Embed(
                title="오류",
                description="자동 역할 설정 추가 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @autorole_group.command(name="제거", description="자동 역할 부여 설정을 제거합니다.")
    @app_commands.describe(역할="제거할 자동 역할 설정")
    @app_commands.default_permissions(manage_roles=True)
    async def remove_autorole(
        self,
        interaction: discord.Interaction,
        역할: discord.Role
    ):
        """자동 역할 부여 설정을 제거합니다."""

        # 권한 확인
        permission_config = permissions.PermissionConfig()
        if not await permission_config.check_user_permission(interaction.user, "manage_roles"):
            embed = discord.Embed(
                title="권한 부족",
                description="역할을 관리할 권한이 없습니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer()

        try:
            # 자동 역할 제거
            result = await remove_autorole(interaction.guild.id, 역할.id)

            if result[0]:  # 성공
                embed = discord.Embed(
                    title="자동 역할 설정 제거 완료",
                    description=f"{역할.mention} 역할의 자동 부여 설정을 제거했습니다.",
                    color=int("a5f0ff", 16)
                )

                embed.add_field(name="제거된 역할", value=역할.mention, inline=True)
                embed.add_field(name="실행자", value=interaction.user.mention, inline=True)

                embed.set_footer(text=f"{format_timestamp(interaction.created_at)}")

                await interaction.followup.send(embed=embed)

                self.logger.info(f"Autorole removed: {역할.name} by {interaction.user}")

            else:  # 실패
                if result[1] == "autorole_not_found":
                    embed = discord.Embed(
                        title="설정 없음",
                        description=f"{역할.mention} 역할은 자동 역할 설정에 등록되어 있지 않습니다.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                else:
                    embed = discord.Embed(
                        title="오류",
                        description="자동 역할 설정 제거 중 오류가 발생했습니다.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Remove autorole command error: {e}")
            embed = discord.Embed(
                title="오류",
                description="자동 역할 설정 제거 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @autorole_group.command(name="목록", description="현재 자동 역할 부여 설정 목록을 표시합니다.")
    @app_commands.default_permissions(manage_roles=True)
    async def list_autorole(self, interaction: discord.Interaction):
        """현재 자동 역할 부여 설정 목록을 표시합니다."""

        # 권한 확인
        permission_config = permissions.PermissionConfig()
        if not await permission_config.check_user_permission(interaction.user, "manage_roles"):
            embed = discord.Embed(
                title="권한 부족",
                description="역할을 관리할 권한이 없습니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer()

        try:
            # 자동 역할 목록 가져오기
            autoroles = await get_autorole(interaction.guild.id)

            embed = discord.Embed(
                title="자동 역할 설정 목록",
                color=int("a5f0ff", 16)
            )

            if len(autoroles) == 0:
                embed.description = "설정된 자동 역할이 없습니다."
            else:
                embed.description = f"자동 역할 설정이 {len(autoroles)}건 있습니다.\n\n"

                for autorole in autoroles:
                    role = interaction.guild.get_role(autorole['role_id'])
                    if role:
                        if autorole['bot_user'] == "all":
                            bot_user = "모든 사용자"
                        elif autorole['bot_user'] == "user":
                            bot_user = "일반 사용자"
                        elif autorole['bot_user'] == "bot":
                            bot_user = "봇"
                        else:
                            bot_user = autorole['bot_user']

                        embed.description += f"• {role.mention} 역할 (부여 대상: 서버에 참가하는 {bot_user})\n"

            embed.set_footer(text=f"{format_timestamp(interaction.created_at)}")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"List autorole command error: {e}")
            embed = discord.Embed(
                title="오류",
                description="자동 역할 설정 목록 조회 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(RoleCommands(bot))