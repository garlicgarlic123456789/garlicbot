"""
GarlicBot Security Commands

보안 관련 명령어들입니다.
"""

import discord
from discord import app_commands
from discord.ext import commands
import re
from cryptography.fernet import Fernet

from config import permissions
from utils.helpers import format_timestamp
from services.database_service import update_anti_raid_settings, get_quarantine_role, get_automod
from utils.helpers import is_blocked
from services.moderation_service import DANGEROUS_PERMISSIONS
from commands.security_check import check_all_bot_admin_perm

# 위험 권한 딕셔너리 (권한 이름 -> 표시 이름)
dangerous_permissions = {
    'ban_members': '멤버 차단',
    'kick_members': '멤버 추방', 
    'manage_channels': '채널 관리',
    'manage_guild': '서버 관리',
    'manage_roles': '역할 관리',
    'administrator': '관리자'
}


class SecurityCommands(commands.Cog):
    """보안 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)

        # 암호화 키 생성 (실제 운영시에는 고정 키 사용 권장)
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)

        # 허용 사용자 ID 리스트
        self.encode_allow_user = [1273450447633645600, 1252894601833087056, 1237634991861665868, 1297882025121812502, 1296053433371066390, 1272449065862303809]
        self.decode_allow_user = [1305492487137267722]

    @app_commands.command(name="보안점검", description="서버의 보안을 점검합니다.")
    @app_commands.describe(
        인증역할="점검할 인증 역할 (기본값: @everyone)",
        관리자역할="관리자 역할 (관리자 채널 권한 점검용)",
        관리자카테고리="관리자 카테고리 (관리자 채널 권한 점검용)"
    )
    @app_commands.default_permissions(administrator=True)
    async def security_check(
        self,
        interaction: discord.Interaction,
        인증역할: discord.Role = None,
        관리자역할: discord.Role = None,
        관리자카테고리: discord.CategoryChannel = None
    ):
        """서버의 보안을 점검합니다."""

        await interaction.response.defer()

        # 차단 사용자 확인
        status, until, reason = is_blocked(interaction.user)
        if status:
            embed = discord.Embed(
                title="사용 제한",
                description=f"보안 점검을 사용할 수 없는 환경입니다.\n\n**사유:** {reason}\n**해제 시각:** {until}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        dangerous = False
        warning = False

        # 검사할 역할 설정
        check_role = 인증역할 if 인증역할 else interaction.guild.default_role
        check_role2 = interaction.guild.default_role if 인증역할 is not None else None

        # 위험 권한 확인
        dangerous_perms_found = []
        for perm, perm_name in dangerous_permissions.items():
            if getattr(check_role.permissions, perm):
                dangerous_perms_found.append(perm_name)
            if check_role2 is not None and getattr(check_role2.permissions, perm):
                dangerous_perms_found.append(perm_name)

        # 임베드 생성
        embed = discord.Embed(
            title="🛡️ 서버 보안 점검 결과",
            description="[보안 가이드 상세보기](https://asdfasdfqwer.notion.site/1fc4a653ce0180038f81f2fb001c7943?source=copy_link)",
        )

        # 역할 권한 보안 점검
        if dangerous_perms_found:
            status_msg = f"⚠️ 일반 사용자에게 위험한 권한 **{len(dangerous_perms_found)}개**가 부여되어 있습니다: {', '.join(dangerous_perms_found)}"
            dangerous = True
        else:
            status_msg = "✅ 일반 사용자에게 위험한 권한이 부여되어 있지 않습니다."

        # 봇 관리자 권한 점검
        all_bot_admin = await check_all_bot_admin_perm(interaction)
        if all_bot_admin:
            bot_admin_msg = "⚠️ 모든 봇에게 관리자 권한을 일괄적으로 부여하는 것은 권장되지 않습니다.\n봇별로 개별적으로 권한을 다르게 부여하시기 바랍니다."
            warning = True
        else:
            bot_admin_msg = "✅ 모든 봇에게 관리자 권한을 일괄적으로 부여하고 있지 않습니다."

        embed.add_field(
            name="🔐 역할 권한 보안",
            value=f"• 일반 사용자 위험 권한: {status_msg}\n• 봇 관리자 권한: {bot_admin_msg}",
            inline=False
        )

        # 채널 권한 보안 점검
        dangerous_channel_perms = []
        for channel in interaction.guild.channels:
            overwrites = channel.overwrites_for(check_role)
            for perm, perm_name in dangerous_permissions.items():
                if getattr(overwrites, perm, None):
                    dangerous_channel_perms.append(f"{channel.mention}: {perm_name}")
            if check_role2 is not None:
                overwrites2 = channel.overwrites_for(check_role2)
                for perm, perm_name in dangerous_permissions.items():
                    if getattr(overwrites2, perm, None):
                        dangerous_channel_perms.append(f"{channel.mention}: {perm_name}")

        if dangerous_channel_perms:
            channel_status_msg = f"⚠️ 일반 사용자에게 위험한 채널 권한 **{len(dangerous_channel_perms)}개**가 부여되어 있습니다: {', '.join(dangerous_channel_perms)}"
            dangerous = True
        else:
            channel_status_msg = "✅ 일반 사용자에게 위험한 채널 권한이 부여되어 있지 않습니다."

        # 관리자 채널 권한 점검
        if 관리자카테고리 is not None:
            admin_channel_access_member = []
            admin_channel_access_role = []
            category_perm = 관리자카테고리.overwrites

            for target, perms in category_perm.items():
                if perms.view_channel == True:
                    if isinstance(target, discord.Member):
                        admin_channel_access_member.append(target)
                    elif isinstance(target, discord.Role):
                        admin_channel_access_role.append(target)

            everyone_role = interaction.guild.default_role
            if (everyone_role not in category_perm or
                category_perm[everyone_role].view_channel == True or
                (category_perm[everyone_role].view_channel is None and everyone_role.permissions.view_channel == True)):
                admin_channel_access_role.append(everyone_role)

            if 관리자역할 is None:
                admin_members_text = [f"<@{member.id}>" for member in admin_channel_access_member]
                admin_roles_text = [f"<@&{role.id}>" for role in admin_channel_access_role]
                admin_roles_text.extend([f"<@&{role.id}>" for role in interaction.guild.roles if role.permissions.administrator])

                if not admin_members_text and not admin_roles_text:
                    admin_access_msg = "관리자 카테고리에 접근 가능한 역할 및 사용자는 다음과 같습니다: *(비어 있음)*"
                else:
                    admin_access_msg = f"관리자 카테고리에 접근 가능한 역할 및 사용자는 다음과 같습니다: {', '.join(admin_members_text + admin_roles_text)}"
            else:
                admin_channel_safe = True
                unexpected_access_members = []
                admin_role_members = [member.id for member in 관리자역할.members]

                for role in admin_channel_access_role:
                    if all(member.bot for member in role.members):
                        continue
                    for member in role.members:
                        if (member.id not in admin_role_members and
                            not member.guild_permissions.administrator and
                            not member.bot):
                            admin_channel_safe = False
                            unexpected_access_members.append(member.mention)

                for member in admin_channel_access_member:
                    if (not member.bot and
                        member.id not in admin_role_members and
                        not member.guild_permissions.administrator):
                        admin_channel_safe = False
                        unexpected_access_members.append(member.mention)

                admin_members_text = [f"<@{member.id}>" for member in admin_channel_access_member]
                admin_roles_text = [f"<@&{role.id}>" for role in admin_channel_access_role]
                admin_roles_text.extend([f"<@&{role.id}>" for role in interaction.guild.roles if role.permissions.administrator])

                if not admin_members_text and not admin_roles_text:
                    admin_access_msg = "관리자 카테고리에 접근 가능한 역할 및 사용자는 다음과 같습니다: *(비어 있음)*"
                else:
                    if not unexpected_access_members:
                        admin_access_msg = f"관리자 카테고리에 접근 가능한 역할 및 사용자는 다음과 같습니다: {', '.join(admin_members_text + admin_roles_text)}"
                    else:
                        dangerous = True
                        admin_access_msg = f"⚠️ 다음 사용자가 관리자 카테고리에 접근이 가능한지 다시 확인해주세요: {', '.join(unexpected_access_members)}\n\n현재 접근 가능한 역할 및 사용자: {', '.join(admin_members_text + admin_roles_text)}"
        else:
            warning = True
            admin_access_msg = "⚠️ 관리자 카테고리가 지정되지 않아 관리자 채널 권한을 점검할 수 없었습니다."

        embed.add_field(
            name="🏠 채널 권한 보안",
            value=f"• 일반 사용자 위험 권한: {channel_status_msg}\n• 관리자 채널 권한: {admin_access_msg}",
            inline=False
        )

        # 자동 검열 보안 점검
        try:
            automod_rules = await interaction.guild.fetch_automod_rules()

            bot_automod = False
            invite_link_keyword_automod = False
            invite_link_keyword_automod2 = False
            invite_link_regex_automod = False

            automod = get_automod(interaction.guild.id)['invite_link'][0]
            if automod == True:
                bot_automod = True

            for automod_rule in automod_rules:
                if invite_link_regex_automod:
                    break
                if automod_rule.enabled:
                    if automod_rule.trigger.regex_patterns is not None:
                        for pattern in automod_rule.trigger.regex_patterns:
                            regex = re.compile(pattern)
                            if (regex.search("discord.gg/discord") is not None and
                                regex.search("discord.com/invite/discord") is not None and
                                regex.search("discord.com:443/invite/discord") is not None and
                                regex.search("discord.gg:443/discord") is not None):
                                invite_link_regex_automod = True
                    if automod_rule.trigger.keyword_filter is not None:
                        for keyword in automod_rule.trigger.keyword_filter:
                            if "discord.gg" in keyword:
                                invite_link_keyword_automod = True
                            if "discord.com/invite" in keyword:
                                invite_link_keyword_automod2 = True

            if bot_automod:
                automod_msg = "✅ 초대 링크 자동 차단: 디스코드 서버 초대 링크를 무단으로 게시하는 것을 차단하는 마늘봇 자동 검열 기능이 활성화되어 있습니다."
            elif invite_link_regex_automod:
                automod_msg = "✅ 초대 링크 자동 차단: 디스코드 서버 초대 링크를 무단으로 게시하는 것을 차단하는 Automod가 활성화되어 있습니다."
            elif invite_link_keyword_automod and invite_link_keyword_automod2:
                automod_msg = "⚠️ 초대 링크 자동 차단: 디스코드 서버 초대 링크를 무단으로 게시하는 것을 차단하는 Automod가 활성화되어 있으나, 정규표현식으로 되어 있지 않거나 정규표현식이 올바르지 않아 일부 우회가 가능합니다."
                warning = True
            else:
                automod_msg = "❌ 초대 링크 자동 차단: 디스코드 서버 초대 링크를 무단으로 게시하는 것을 차단하는 Automod가 활성화되어 있지 않습니다."
                dangerous = True

        except Exception as e:
            self.logger.error(f"Automod check error: {e}")
            automod_msg = "❓ 자동 검열 상태를 확인할 수 없습니다."

        embed.add_field(
            name="🤖 자동 검열 보안",
            value=automod_msg,
            inline=False
        )

        # 색상 설정
        if dangerous:
            embed.color = discord.Color.red()
        elif warning:
            embed.color = discord.Color.yellow()
        else:
            embed.color = int("a5f0ff", 16)

        embed.set_footer(text=f"{format_timestamp(interaction.created_at)}")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="암호화", description="메시지를 암호화합니다.")
    @app_commands.describe(메시지="암호화할 메시지")
    async def encode(self, interaction: discord.Interaction, 메시지: str):
        """메시지를 암호화합니다."""

        user_id = interaction.user.id

        # 권한 확인 (현재는 모든 사용자 허용으로 설정됨)
        if True:  # user_id in self.encode_allow_user
            try:
                encrypted_message = self.cipher.encrypt(메시지.encode()).decode()
                self.logger.info(f"Message encrypted by {interaction.user}: {메시지[:50]}...")
                await interaction.response.send_message(
                    f"🔐 **암호화된 메시지:**\n```\n{encrypted_message}\n```",
                    ephemeral=True
                )
            except Exception as e:
                self.logger.error(f"Encryption error: {e}")
                await interaction.response.send_message(
                    "❌ 암호화 중 오류가 발생했습니다.",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                "❌ 명령어 사용 권한이 부족합니다.",
                ephemeral=True
            )

    @app_commands.command(name="복호화", description="암호화된 메시지를 해독합니다.")
    @app_commands.describe(메시지="복호화할 암호화된 메시지")
    async def decode(self, interaction: discord.Interaction, 메시지: str):
        """암호화된 메시지를 해독합니다."""

        user_id = interaction.user.id

        # 권한 확인
        if user_id in self.decode_allow_user:
            try:
                decrypted_message = self.cipher.decrypt(메시지.encode()).decode()
                self.logger.info(f"Message decrypted by {interaction.user}: {decrypted_message[:50]}...")
                await interaction.response.send_message(
                    f"🔓 **해독된 메시지:**\n```\n{decrypted_message}\n```",
                    ephemeral=True
                )
            except Exception as e:
                self.logger.error(f"Decryption error: {e}")
                await interaction.response.send_message(
                    "❌ 해독에 실패했습니다. 올바른 암호화된 메시지인지 확인해주세요.",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                "❌ 명령어 사용 권한이 부족합니다.",
                ephemeral=True
            )


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(SecurityCommands(bot))