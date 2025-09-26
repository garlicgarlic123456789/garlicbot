"""
GarlicBot XP Commands

경험치 및 레벨링 관련 명령어들입니다.
"""

import discord
from discord import app_commands
from discord.ext import commands

from config import permissions
from utils.helpers import format_timestamp


class XPCommands(commands.Cog):
    """경험치 및 레벨링 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)

    def return_level(self, exp: int) -> int:
        """경험치로부터 레벨을 계산합니다."""
        if exp >= 7500000: return 50
        elif exp >= 6800000: return 49
        elif exp >= 6100000: return 48
        elif exp >= 5500000: return 47
        elif exp >= 4900000: return 46
        elif exp >= 4400000: return 45
        elif exp >= 3950000: return 44
        elif exp >= 3450000: return 43
        elif exp >= 3000000: return 42
        elif exp >= 2600000: return 41
        elif exp >= 2200000: return 40
        elif exp >= 1850000: return 39
        elif exp >= 1550000: return 38
        elif exp >= 1300000: return 37
        elif exp >= 1100000: return 36
        elif exp >= 880000: return 35
        elif exp >= 670000: return 34
        elif exp >= 500000: return 33
        elif exp >= 350000: return 32
        elif exp >= 270000: return 31
        elif exp >= 220000: return 30
        elif exp >= 180000: return 29
        elif exp >= 150000: return 28
        elif exp >= 127000: return 27
        elif exp >= 109000: return 26
        elif exp >= 93000: return 25
        elif exp >= 79000: return 24
        elif exp >= 67000: return 23
        elif exp >= 57000: return 22
        elif exp >= 48000: return 21
        elif exp >= 40000: return 20
        elif exp >= 33000: return 19
        elif exp >= 27000: return 18
        elif exp >= 22000: return 17
        elif exp >= 18700: return 16
        elif exp >= 15700: return 15
        elif exp >= 13000: return 14
        elif exp >= 10500: return 13
        elif exp >= 8200: return 12
        elif exp >= 6500: return 11
        elif exp >= 5000: return 10
        elif exp >= 3700: return 9
        elif exp >= 2700: return 8
        elif exp >= 2000: return 7
        elif exp >= 1500: return 6
        elif exp >= 1000: return 5
        elif exp >= 500: return 4
        elif exp >= 300: return 3
        elif exp >= 150: return 2
        else: return 1

    def get_exp_for_level(self, level: int) -> int:
        """특정 레벨에 도달하기 위해 필요한 최소 경험치를 반환합니다."""
        level_requirements = {
            1: 0, 2: 150, 3: 300, 4: 500, 5: 1000, 6: 1500, 7: 2000, 8: 2700, 9: 3700, 10: 5000,
            11: 6500, 12: 8200, 13: 10500, 14: 13000, 15: 15700, 16: 18700, 17: 22000, 18: 27000,
            19: 33000, 20: 40000, 21: 48000, 22: 57000, 23: 67000, 24: 79000, 25: 93000, 26: 109000,
            27: 127000, 28: 150000, 29: 180000, 30: 220000, 31: 270000, 32: 350000, 33: 500000,
            34: 670000, 35: 880000, 36: 1100000, 37: 1300000, 38: 1550000, 39: 1850000, 40: 2200000,
            41: 2600000, 42: 3000000, 43: 3450000, 44: 3950000, 45: 4400000, 46: 4900000, 47: 5500000,
            48: 6100000, 49: 6800000, 50: 7500000
        }
        return level_requirements.get(level, 0)

    @app_commands.command(name="레벨", description="사용자의 레벨과 경험치를 확인합니다.")
    @app_commands.describe(사용자="확인할 사용자 (기본값: 자신)")
    async def check_level(
        self,
        interaction: discord.Interaction,
        사용자: discord.Member = None
    ):
        """사용자의 레벨과 경험치를 확인합니다."""

        target_user = 사용자 or interaction.user

        try:
            # TODO: 데이터베이스에서 사용자 경험치 조회 로직 구현
            # 현재는 임시로 0으로 설정
            user_exp = 0
            user_money = 0

            current_level = self.return_level(user_exp)
            exp_for_current = self.get_exp_for_level(current_level)
            exp_for_next = self.get_exp_for_level(current_level + 1)

            embed = discord.Embed(
                title=f"{target_user.display_name}의 레벨 정보",
                color=int("a5f0ff", 16)
            )

            embed.add_field(
                name="현재 레벨",
                value=f"**{current_level}**",
                inline=True
            )

            embed.add_field(
                name="현재 경험치",
                value=f"{user_exp:,} XP",
                inline=True
            )

            embed.add_field(
                name="보유 금액",
                value=f"{user_money:,}원",
                inline=True
            )

            if current_level < 50:
                progress = exp_for_next - exp_for_current
                current_progress = user_exp - exp_for_current
                percentage = min(100, (current_progress / progress) * 100) if progress > 0 else 100

                embed.add_field(
                    name="다음 레벨까지",
                    value=f"{current_progress:,}/{progress:,} XP ({percentage:.1f}%)",
                    inline=False
                )

                # 진행 바 생성
                filled = int(percentage / 10)
                bar = "█" * filled + "░" * (10 - filled)
                embed.add_field(
                    name="진행률",
                    value=f"`{bar}`",
                    inline=False
                )
            else:
                embed.add_field(
                    name="상태",
                    value="🎉 **최고 레벨 달성!**",
                    inline=False
                )

            embed.set_thumbnail(url=target_user.avatar.url if target_user.avatar else None)
            embed.set_footer(text=f"{format_timestamp(interaction.created_at)}")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            self.logger.error(f"Level check command error: {e}")
            embed = discord.Embed(
                title="오류",
                description="레벨 정보 조회 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="경험치설정", description="경험치 기능을 설정합니다.")
    @app_commands.describe(
        기능사용여부="경험치 기능을 켜거나 끕니다.",
        채팅경험치="채팅 경험치 양을 설정합니다.",
        채팅경험치쿨다운="채팅 경험치 쿨다운(단위: 초)을 설정합니다.",
        음성경험치="음성 경험치 양을 설정합니다.",
        음성경험치쿨다운="음성 경험치 쿨다운(단위: 초)을 설정합니다.",
        단위="경험치 단위를 설정합니다."
    )
    @app_commands.default_permissions(administrator=True)
    async def setup_xp(
        self,
        interaction: discord.Interaction,
        기능사용여부: bool,
        채팅경험치: int = None,
        채팅경험치쿨다운: int = None,
        음성경험치: int = None,
        음성경험치쿨다운: int = None,
        단위: str = None
    ):
        """경험치 기능을 설정합니다."""

        # 권한 확인
        permission_config = permissions.PermissionConfig()
        if not await permission_config.check_user_permission(interaction.user, "administrator"):
            embed = discord.Embed(
                title="권한 부족",
                description="이 명령어를 사용하려면 관리자 권한이 필요합니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer()

        # 입력값 검증
        if 기능사용여부 and (채팅경험치 is None or 음성경험치 is None or
                           채팅경험치쿨다운 is None or 음성경험치쿨다운 is None):
            embed = discord.Embed(
                title="입력 오류",
                description="경험치 기능을 활성화하려면 모든 필수 값(채팅/음성 경험치, 쿨다운)을 입력해야 합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # 값 범위 검증
        if 채팅경험치 is not None and (채팅경험치 < 1 or 채팅경험치 > 100):
            embed = discord.Embed(
                title="입력 오류",
                description="채팅 경험치는 1-100 사이의 값이어야 합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        if 음성경험치 is not None and (음성경험치 < 1 or 음성경험치 > 100):
            embed = discord.Embed(
                title="입력 오류",
                description="음성 경험치는 1-100 사이의 값이어야 합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        if 채팅경험치쿨다운 is not None and (채팅경험치쿨다운 < 10 or 채팅경험치쿨다운 > 3600):
            embed = discord.Embed(
                title="입력 오류",
                description="채팅 경험치 쿨다운은 10-3600초 사이의 값이어야 합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        if 음성경험치쿨다운 is not None and (음성경험치쿨다운 < 10 or 음성경험치쿨다운 > 3600):
            embed = discord.Embed(
                title="입력 오류",
                description="음성 경험치 쿨다운은 10-3600초 사이의 값이어야 합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        try:
            # TODO: 데이터베이스 업데이트 로직 구현
            # update_xp_setting(interaction.guild.id, 기능사용여부, 채팅경험치,
            #                  채팅경험치쿨다운, 음성경험치, 음성경험치쿨다운, 단위)

            if not 기능사용여부:
                embed = discord.Embed(
                    title="경험치 기능 비활성화",
                    description="경험치 기능이 성공적으로 비활성화되었습니다.",
                    color=int("a5f0ff", 16)
                )
            else:
                embed = discord.Embed(
                    title="경험치 기능 설정 완료",
                    description="경험치 기능이 성공적으로 설정되었습니다.",
                    color=int("a5f0ff", 16)
                )

                embed.add_field(
                    name="채팅 경험치",
                    value=f"{채팅경험치} XP",
                    inline=True
                )
                embed.add_field(
                    name="채팅 쿨다운",
                    value=f"{채팅경험치쿨다운}초",
                    inline=True
                )
                embed.add_field(
                    name="음성 경험치",
                    value=f"{음성경험치} XP",
                    inline=True
                )
                embed.add_field(
                    name="음성 쿨다운",
                    value=f"{음성경험치쿨다운}초",
                    inline=True
                )
                if 단위:
                    embed.add_field(
                        name="경험치 단위",
                        value=단위,
                        inline=True
                    )

            embed.add_field(
                name="설정자",
                value=interaction.user.mention,
                inline=False
            )

            embed.set_footer(text=f"{format_timestamp(interaction.created_at)}")

            await interaction.followup.send(embed=embed)

            self.logger.info(f"XP settings updated by {interaction.user} in {interaction.guild.name}")

        except Exception as e:
            self.logger.error(f"XP setup command error: {e}")
            embed = discord.Embed(
                title="오류",
                description="경험치 설정 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(XPCommands(bot))