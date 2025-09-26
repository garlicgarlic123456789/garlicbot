"""
GarlicBot Moderation Commands

관리 및 조정 관련 명령어들입니다.
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import pytz
from typing import List, Tuple, Any

from config import permissions, constants
from utils.helpers import format_timestamp


class ModerationCommands(commands.Cog):
    """관리 및 조정 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)

    def is_blocked(self, user: discord.User) -> Tuple[bool, str, str]:
        """사용자가 차단되었는지 확인합니다."""
        # TODO: 차단 사용자 데이터 로드 로직 구현
        # 현재는 임시로 차단되지 않은 것으로 반환
        return False, None, None

    def is_valid_time(self, time_str: str) -> bool:
        """시간 문자열 형식이 유효한지 확인합니다."""
        try:
            datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            return True
        except ValueError:
            return False

    async def add_timeout(
        self,
        user: discord.Member,
        seconds: int,
        reason: str = None,
        ignore_ongoing_timeout: bool = False
    ) -> None:
        """사용자에게 타임아웃을 적용합니다."""
        if ignore_ongoing_timeout:
            new_timeout = discord.utils.utcnow() + timedelta(seconds=seconds)
        else:
            if user.timed_out_until and user.timed_out_until > discord.utils.utcnow():
                # 기존 타임아웃 시간에 추가
                new_timeout = user.timed_out_until + timedelta(seconds=seconds)
            else:
                # 현재 시간에서 타임아웃 시간 계산
                new_timeout = discord.utils.utcnow() + timedelta(seconds=seconds)

        await user.edit(timed_out_until=new_timeout, reason=reason)

    @app_commands.command(name="슬로우모드", description="채널의 슬로우모드를 설정합니다.")
    @app_commands.describe(
        시간="슬로우모드 시간 (초 단위, 0-21600)",
        채널="설정할 채널 (기본값: 현재 채널)"
    )
    @app_commands.default_permissions(manage_channels=True)
    async def set_slowmode(
        self,
        interaction: discord.Interaction,
        시간: int,
        채널: discord.TextChannel = None
    ):
        """채널의 슬로우모드를 설정합니다."""

        # 권한 확인
        permission_config = permissions.PermissionConfig()
        if not await permission_config.check_user_permission(interaction.user, "manage_channels"):
            await interaction.response.send_message(
                f"**[오류!]** {interaction.user.mention}님은 채널을 관리할 권한이 없습니다.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # 입력값 검증
        if 시간 < 0:
            embed = discord.Embed(
                title="입력 오류",
                description="슬로우모드 시간은 0초 이상이어야 합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        if 시간 > 60 * 60 * 6:  # 6시간 = 21600초
            embed = discord.Embed(
                title="입력 오류",
                description="슬로우모드 시간은 6시간(21,600초) 이하여야 합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # 채널 설정
        target_channel = 채널 or interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            embed = discord.Embed(
                title="오류",
                description="텍스트 채널에서만 슬로우모드를 설정할 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        try:
            await target_channel.edit(slowmode_delay=시간)

            # 시간 포맷팅
            if 시간 == 0:
                time_desc = "비활성화"
            elif 시간 < 60:
                time_desc = f"{시간}초"
            elif 시간 < 3600:
                minutes = 시간 // 60
                seconds = 시간 % 60
                time_desc = f"{minutes}분"
                if seconds > 0:
                    time_desc += f" {seconds}초"
            else:
                hours = 시간 // 3600
                minutes = (시간 % 3600) // 60
                time_desc = f"{hours}시간"
                if minutes > 0:
                    time_desc += f" {minutes}분"

            embed = discord.Embed(
                title="슬로우모드 설정 완료",
                description=f"{target_channel.mention} 채널의 슬로우모드가 설정되었습니다.",
                color=int("a5f0ff", 16)
            )

            embed.add_field(name="설정 시간", value=time_desc, inline=True)
            embed.add_field(name="설정자", value=interaction.user.mention, inline=True)

            embed.set_footer(text=f"{format_timestamp(interaction.created_at)}")

            await interaction.followup.send(embed=embed)

            self.logger.info(f"Slowmode set by {interaction.user} in {target_channel.name}: {시간} seconds")

        except discord.Forbidden:
            embed = discord.Embed(
                title="권한 부족",
                description="봇에게 채널을 관리할 권한이 없습니다.\n\n**필요한 권한:** `채널 관리하기`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Slowmode command error: {e}")
            embed = discord.Embed(
                title="오류",
                description="슬로우모드 설정 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(ModerationCommands(bot))

import discord
from discord import app_commands
from discord.ext import commands

from config import permissions
from utils.helpers import format_timestamp


class ModerationCommands(commands.Cog):
    """관리 및 조정 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)

    @app_commands.command(name="슬로우모드", description="채널의 슬로우모드를 설정합니다.")
    @app_commands.describe(
        시간="슬로우모드 시간 (초 단위, 0-21600)",
        채널="설정할 채널 (기본값: 현재 채널)"
    )
    @app_commands.default_permissions(manage_channels=True)
    async def set_slowmode(
        self,
        interaction: discord.Interaction,
        시간: int,
        채널: discord.TextChannel = None
    ):
        """채널의 슬로우모드를 설정합니다."""

        # 권한 확인
        permission_config = permissions.PermissionConfig()
        if not await permission_config.check_user_permission(interaction.user, "manage_channels"):
            await interaction.response.send_message(
                f"**[오류!]** {interaction.user.mention}님은 채널을 관리할 권한이 없습니다.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # 입력값 검증
        if 시간 < 0:
            embed = discord.Embed(
                title="입력 오류",
                description="슬로우모드 시간은 0초 이상이어야 합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        if 시간 > 60 * 60 * 6:  # 6시간 = 21600초
            embed = discord.Embed(
                title="입력 오류",
                description="슬로우모드 시간은 6시간(21,600초) 이하여야 합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # 채널 설정
        target_channel = 채널 or interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            embed = discord.Embed(
                title="오류",
                description="텍스트 채널에서만 슬로우모드를 설정할 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        try:
            await target_channel.edit(slowmode_delay=시간)

            # 시간 포맷팅
            if 시간 == 0:
                time_desc = "비활성화"
            elif 시간 < 60:
                time_desc = f"{시간}초"
            elif 시간 < 3600:
                minutes = 시간 // 60
                seconds = 시간 % 60
                time_desc = f"{minutes}분"
                if seconds > 0:
                    time_desc += f" {seconds}초"
            else:
                hours = 시간 // 3600
                minutes = (시간 % 3600) // 60
                time_desc = f"{hours}시간"
                if minutes > 0:
                    time_desc += f" {minutes}분"

            embed = discord.Embed(
                title="슬로우모드 설정 완료",
                description=f"{target_channel.mention} 채널의 슬로우모드가 설정되었습니다.",
                color=int("a5f0ff", 16)
            )

            embed.add_field(name="설정 시간", value=time_desc, inline=True)
            embed.add_field(name="설정자", value=interaction.user.mention, inline=True)

            embed.set_footer(text=f"{format_timestamp(interaction.created_at)}")

            await interaction.followup.send(embed=embed)

            self.logger.info(f"Slowmode set by {interaction.user} in {target_channel.name}: {시간} seconds")

        except discord.Forbidden:
            embed = discord.Embed(
                title="권한 부족",
                description="봇에게 채널을 관리할 권한이 없습니다.\n\n**필요한 권한:** `채널 관리하기`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Slowmode command error: {e}")
            embed = discord.Embed(
                title="오류",
                description="슬로우모드 설정 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)


async def setup(bot):
    """Cog를 봇에 추가합니다."""

    @app_commands.command(name="일괄취소", description="특정 사용자의 특정 시각 이후 관리 권한 사용 행위를 실행취소합니다.")
    @app_commands.describe(
        시각="취소 범위의 시작 지점을 입력해 주세요. (형식: YYYY-MM-DD HH:MM:SS)",
        사용자="어느 사용자의 행위를 실행취소할지 입력해 주세요.",
        사유="취소 사유 (선택사항)"
    )
    async def bulk_cancel(
        self,
        interaction: discord.Interaction,
        시각: str,
        사용자: discord.User,
        사유: str = None
    ):
        """특정 사용자의 특정 시각 이후 관리 권한 사용 행위를 실행취소합니다."""

        # 서버 주인 권한 확인
        if interaction.guild.owner_id != interaction.user.id:
            embed = discord.Embed(
                title="권한 부족",
                description="이 명령어는 서버 주인만 사용할 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # 사용자 차단 상태 확인
        status, until, reason = self.is_blocked(interaction.user)
        if status:
            msg = f"**[오류!]** {interaction.user.mention}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.response.send_message(msg, ephemeral=True)
            return

        # 시각 형식 검증
        시각 = 시각.replace("\\", "")
        if not self.is_valid_time(시각):
            embed = discord.Embed(
                title="입력 오류",
                description="유효하지 않은 시각 형식입니다. 올바른 형식으로 입력해 주세요.\n\n**형식:** `YYYY-MM-DD HH:MM:SS`",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # 시각 문자열을 datetime 객체로 변환
        time_obj = datetime.strptime(시각, "%Y-%m-%d %H:%M:%S")
        time_obj = constants.KST.localize(time_obj)

        await interaction.response.defer()

        # 감사 로그 조회
        logs = []
        async for log in interaction.guild.audit_logs(after=time_obj, user=사용자, oldest_first=False):
            logs.append(log)

        # 오래된 순으로 로그 정렬
        logs.sort(key=lambda x: x.created_at)

        # 감사 로그 처리
        canceling_actions = []
        for log in logs:
            await self._process_audit_log(log, canceling_actions)

        # 작업 실행 취소
        action_all = len(canceling_actions)
        action_cnt = 0
        action_error_cnt = 0

        if 사유 is None:
            reason = f"사용자 {interaction.user.name} ({interaction.user.id}) 의 /일괄취소 명령어 사용"
            사유 = "*(사유 입력되지 않음)*"
        else:
            reason = f"사용자 {interaction.user.name} ({interaction.user.id}) 의 /일괄취소 명령어 사용 (사유: {사유})"

        for action in canceling_actions:
            success = await self._execute_cancel_action(action, reason)
            if success:
                action_cnt += 1
            else:
                action_error_cnt += 1

        # 결과 임베드 생성
        embed = discord.Embed(
            title="일괄 취소 완료",
            description=f"{사용자.mention} 사용자의 작업 {action_all}개 중 {action_cnt}개를 실행취소했습니다.\n\n잘못 실행취소한 경우 마늘이의 작업을 다시 일괄적으로 실행취소할 수 있습니다.",
            color=int("a5f0ff", 16)
        )

        embed.add_field(name="대상 사용자", value=f"{사용자.mention}", inline=False)
        embed.add_field(name="대상 기간", value=f"{시각} ~ 현재 시각", inline=False)
        embed.add_field(name="대상 작업", value=f"작업 {action_all}개 중 {action_cnt}개", inline=False)
        embed.add_field(name="관리자", value=f"{interaction.user.mention}", inline=False)
        embed.add_field(name="사유", value=사유, inline=False)

        await interaction.followup.send(embed=embed)

        # 로그 기록
        await self._log_bulk_cancel(interaction, 사용자, 시각, action_all, action_cnt, 사유)

        self.logger.info(f"Bulk cancel by {interaction.user} for {사용자}: {action_cnt}/{action_all} actions canceled")

    async def _process_audit_log(self, log: discord.AuditLogEntry, canceling_actions: List[List[Any]]):
        """감사 로그를 처리하여 취소할 작업 목록을 생성합니다."""
        try:
            if log.action == discord.AuditLogAction.ban:
                canceling_actions.append(['ban', log.target])

            elif log.action == discord.AuditLogAction.unban:
                canceling_actions.append(['unban', log.target])

            elif log.action == discord.AuditLogAction.member_update:
                await self._process_member_update(log, canceling_actions)

            elif log.action == discord.AuditLogAction.member_role_update:
                await self._process_role_update(log, canceling_actions)

            elif log.action == discord.AuditLogAction.role_update:
                canceling_actions.append(['role_update', log.target.id, dict(log.before)])

            elif log.action == discord.AuditLogAction.channel_update:
                canceling_actions.append(['channel_update', log.target, dict(log.before)])

            elif log.action == discord.AuditLogAction.overwrite_create:
                canceling_actions.append(['overwrite_create', log.target, log.extra])

            elif log.action == discord.AuditLogAction.overwrite_update:
                before_allow = log.before.get('allow', 0) if log.before else 0
                before_deny = log.before.get('deny', 0) if log.before else 0
                po = discord.PermissionOverwrite.from_pair(
                    allow=discord.Permissions(before_allow),
                    deny=discord.Permissions(before_deny)
                )
                canceling_actions.append(['overwrite_update', log.target, log.extra, po])

            elif log.action == discord.AuditLogAction.overwrite_delete:
                before_allow = log.before.get('allow', 0) if log.before else 0
                before_deny = log.before.get('deny', 0) if log.before else 0
                po = discord.PermissionOverwrite.from_pair(
                    allow=discord.Permissions(before_allow),
                    deny=discord.Permissions(before_deny)
                )
                canceling_actions.append(['overwrite_delete', log.target, log.extra, po])

            elif log.action == discord.AuditLogAction.guild_update:
                canceling_actions.append(['guild_update', log.target, dict(log.before)])

        except Exception as e:
            self.logger.error(f"Error processing audit log {log.id}: {e}")

    async def _process_member_update(self, log: discord.AuditLogEntry, canceling_actions: List[List[Any]]):
        """멤버 업데이트 로그를 처리합니다."""
        try:
            if hasattr(log.changes, 'after') and hasattr(log.changes, 'before'):
                # 타임아웃 설정
                if (log.changes.after.timed_out_until is not None and
                    log.changes.before.timed_out_until is None):
                    canceling_actions.append(['timeout', log.target])

                # 타임아웃 해제
                elif (log.changes.after.timed_out_until is None and
                      log.changes.before.timed_out_until is not None):
                    canceling_actions.append(['untimeout', log.target, log.changes.before.timed_out_until])

                # 닉네임 변경
                if log.changes.after.nick != log.changes.before.nick:
                    canceling_actions.append(['nick_change', log.target, log.changes.before.nick])

        except Exception as e:
            self.logger.error(f"Error processing member update: {e}")

    async def _process_role_update(self, log: discord.AuditLogEntry, canceling_actions: List[List[Any]]):
        """역할 업데이트 로그를 처리합니다."""
        try:
            before_roles = [role for role in log.changes.before.roles if hasattr(role, 'id')]
            after_roles = [role for role in log.changes.after.roles if hasattr(role, 'id')]

            # 역할이 제거된 경우
            if before_roles and not after_roles:
                for role in before_roles:
                    canceling_actions.append(['role_revoke', log.target, role])

            # 역할이 부여된 경우
            elif after_roles and not before_roles:
                for role in after_roles:
                    canceling_actions.append(['role_grant', log.target, role])

        except Exception as e:
            self.logger.error(f"Error processing role update: {e}")

    async def _execute_cancel_action(self, action: List[Any], reason: str) -> bool:
        """취소 작업을 실행합니다."""
        try:
            action_type = action[0]

            if action_type == 'ban':
                await action[1].guild.unban(action[1], reason=reason)

            elif action_type == 'unban':
                await action[1].guild.ban(action[1], reason=reason)

            elif action_type == 'nick_change':
                await action[1].edit(nick=action[2], reason=reason)

            elif action_type == 'timeout':
                await action[1].edit(timed_out_until=None, reason=reason)

            elif action_type == 'untimeout':
                await action[1].edit(timed_out_until=action[2], reason=reason)

            elif action_type == 'role_revoke':
                await action[1].add_roles(action[2], reason=reason)

            elif action_type == 'role_grant':
                await action[1].remove_roles(action[2], reason=reason)

            elif action_type == 'channel_update':
                await action[1].edit(reason=reason, **action[2])

            elif action_type == 'role_update':
                role = action[1].guild.get_role(action[1])
                if role:
                    await role.edit(reason=reason, **action[2])

            elif action_type == 'overwrite_create':
                await action[1].set_permissions(action[2], overwrite=None, reason=reason)

            elif action_type == 'overwrite_update':
                await action[1].set_permissions(action[2], overwrite=action[3], reason=reason)

            elif action_type == 'overwrite_delete':
                await action[1].set_permissions(action[2], overwrite=action[3], reason=reason)

            elif action_type == 'guild_update':
                await action[1].guild.edit(reason=reason, **action[2])

            return True

        except Exception as e:
            self.logger.error(f"Error executing cancel action {action}: {e}")
            return False

    async def _log_bulk_cancel(self, interaction: discord.Interaction, 사용자: discord.User,
                              시각: str, action_all: int, action_cnt: int, 사유: str):
        """일괄 취소 작업을 로그 채널에 기록합니다."""
        try:
            # 메인 서버에서만 로그 기록
            if interaction.guild.id != constants.USING_SERVER:
                return

            embed = discord.Embed(
                title="일괄 취소",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="대상 사용자", value=f"{사용자.mention}", inline=False)
            embed.add_field(name="대상 기간", value=f"{시각} ~ 현재 시각", inline=False)
            embed.add_field(name="대상 작업", value=f"작업 {action_all}개 중 {action_cnt}개", inline=False)
            embed.add_field(name="관리자", value=f"{interaction.user.mention}", inline=False)
            embed.add_field(name="사유", value=사유, inline=False)

            # 기록 채널에 전송
            record_channel = self.bot.get_channel(constants.RECORD_CHANNEL)
            if record_channel:
                await record_channel.send(embed=embed)

            # 메시지 로그 채널에도 전송
            log_channel = self.bot.get_channel(constants.MESSAGE_LOG)
            if log_channel:
                await log_channel.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error logging bulk cancel: {e}")


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(ModerationCommands(bot))
