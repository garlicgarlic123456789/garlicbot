"""
GarlicBot Encode Commands

암호화/복호화 관련 명령어들입니다.
"""

import discord
from discord import app_commands
from discord.ext import commands
from cryptography.fernet import Fernet

from utils.helpers import is_blocked


class EncodeCog(commands.Cog):
    """암호화/복호화 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)

        # 암호화 키 및 cipher 초기화
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)

        # 허용 사용자 ID 리스트
        self.encode_allow_user = [
            1273450447633645600, 1252894601833087056, 1237634991861665868,
            1297882025121812502, 1296053433371066390, 1272449065862303809
        ]  # 암호화 권한 사용자
        self.decode_allow_user = [1305492487137267722]  # 해독 권한 사용자

    @app_commands.command(name="encode", description="메시지를 암호화합니다.")
    @app_commands.describe(message="암호화할 메시지")
    async def encode(self, interaction: discord.Interaction, message: str):
        """메시지를 암호화합니다."""
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

        user_id = interaction.user.id
        user_name = interaction.user.name

        # 암호화 권한 확인 (현재는 모든 사용자 허용)
        if True:  # user_id in self.encode_allow_user:
            try:
                encrypted_message = self.cipher.encrypt(message.encode()).decode()

                # 로그 기록
                self.logger.info(f'User {user_name}({user_id}) encrypted message: {message[:50]}...')

                embed = discord.Embed(
                    title="🔐 메시지 암호화 완료",
                    description=f"**암호화된 메시지:**\n```{encrypted_message}```",
                    color=int("a5f0ff", 16)
                )
                embed.set_footer(text=f"요청자: {interaction.user.display_name}")

                await interaction.followup.send(embed=embed, ephemeral=True)

            except Exception as e:
                self.logger.error(f"Encryption error: {e}")
                embed = discord.Embed(
                    title="오류",
                    description="메시지 암호화 중 오류가 발생했습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="오류",
                description="명령어 사용 권한이 부족합니다.\n`encode_allow_user` 그룹에 속한 사용자만 사용할 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="decode", description="암호화된 메시지를 해독합니다.")
    @app_commands.describe(message="해독할 암호화된 메시지")
    async def decode(self, interaction: discord.Interaction, message: str):
        """암호화된 메시지를 해독합니다."""
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

        user_id = interaction.user.id
        user_name = interaction.user.name

        # 해독 권한 확인
        if user_id in self.decode_allow_user:
            try:
                decrypted_message = self.cipher.decrypt(message.encode()).decode()

                # 로그 기록
                self.logger.info(f'User {user_name}({user_id}) decrypted message: {message[:50]}...')

                embed = discord.Embed(
                    title="🔓 메시지 해독 완료",
                    description=f"**해독된 메시지:**\n```{decrypted_message}```",
                    color=int("a5f0ff", 16)
                )
                embed.set_footer(text=f"요청자: {interaction.user.display_name}")

                await interaction.followup.send(embed=embed, ephemeral=True)

            except Exception as e:
                self.logger.error(f"Decryption error: {e}")
                embed = discord.Embed(
                    title="오류",
                    description="메시지 해독에 실패했습니다.\n올바른 암호화된 메시지인지 확인해주세요.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="오류",
                description="명령어 사용 권한이 부족합니다.\n`decode_allow_user` 그룹에 속한 사용자만 사용할 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(EncodeCog(bot))