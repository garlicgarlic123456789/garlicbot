"""
GarlicBot Moderation Events

조치 관련 모든 이벤트를 처리하는 모듈입니다.
- on_member_ban: 멤버 차단 처리
- on_member_unban: 멤버 차단 해제 처리
- 안티 누크 감지 및 처리
"""

import discord
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
from typing import Optional, Dict, Any

from config import settings, constants
from core.exceptions import GarlicBotException


class ModerationEvents(commands.Cog):
    """조치 관련 이벤트 핸들러"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # 안티 누크 관련 변수
        self.ban_time_list = {}
        self.temp_ban_tracking = {}
    
    # ============== 차단 관련 이벤트 ==============
    
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """멤버 차단 시 처리"""
        try:
            if guild.id != settings.USING_SERVER_ID:
                return
            
            # 안티 누크 검사
            await self._check_anti_nuke_ban(guild, user)
            
            # 차단 로그 기록
            await self._log_member_ban(guild, user)
            
        except Exception as e:
            self.bot.logger.error(f"Error in on_member_ban: {e}", exc_info=True)
    
    async def _check_anti_nuke_ban(self, guild: discord.Guild, user: discord.User):
        """안티 누크 차단 감지"""
        # 감사 로그에서 차단 실행자 찾기
        async for entry in guild.audit_logs(
            action=discord.AuditLogAction.ban, 
            limit=1
        ):
            if entry.target.id == user.id:
                admin_id = entry.user.id
                
                # 화이트리스트 체크
                admin_member = guild.get_member(admin_id)
                if admin_member:
                    whitelist_roles = [guild.get_role(role_id) for role_id in settings.ANTI_NUKE_WHITELIST]
                    if any(role in admin_member.roles for role in whitelist_roles if role):
                        return
                
                # 차단 횟수 추적
                await self._process_anti_nuke_ban(guild.id, admin_id, guild)
                break
    
    async def _process_anti_nuke_ban(self, server_id: int, admin_id: int, guild: discord.Guild):
        """안티 누크 차단 처리"""
        current_time = datetime.utcnow()
        
        # 서버별 차단 시간 추적
        if server_id not in self.ban_time_list:
            self.ban_time_list[server_id] = {}
        
        if admin_id not in self.ban_time_list[server_id]:
            self.ban_time_list[server_id][admin_id] = []
        
        # 현재 시간 추가
        self.ban_time_list[server_id][admin_id].append(current_time)
        
        # 10분 이내의 차간만 유지
        cutoff_time = current_time - timedelta(minutes=10)
        self.ban_time_list[server_id][admin_id] = [
            ban_time for ban_time in self.ban_time_list[server_id][admin_id]
            if ban_time > cutoff_time
        ]
        
        # 차단 횟수 확인
        ban_count = len(self.ban_time_list[server_id][admin_id])
        
        if ban_count > settings.BAN_NUKE_COUNT:
            # 누크 감지 - 권한 회수
            await self._handle_nuke_detection(admin_id, guild)
    
    async def _handle_nuke_detection(self, admin_id: int, guild: discord.Guild):
        """누크 감지 시 처리"""
        admin_member = guild.get_member(admin_id)
        if not admin_member:
            return
        
        # 위험한 권한들 회수
        dangerous_permissions = [
            'ban_members', 'kick_members', 'manage_channels',
            'manage_guild', 'manage_roles', 'administrator'
        ]
        
        removed_roles = []
        
        for role in admin_member.roles:
            if role == guild.default_role:
                continue
                
            # 역할의 권한 확인
            role_perms = role.permissions
            has_dangerous_perm = any(
                getattr(role_perms, perm, False) for perm in dangerous_permissions
            )
            
            if has_dangerous_perm:
                try:
                    await admin_member.remove_roles(role, reason="안티 누크: 대량 차단 감지")
                    removed_roles.append(role.name)
                except discord.Forbidden:
                    pass
        
        # 알림 전송
        await self._send_nuke_alert(guild, admin_member, removed_roles)
    
    async def _send_nuke_alert(self, guild: discord.Guild, admin_member: discord.Member, removed_roles: list):
        """누크 감지 알림 전송"""
        alert_channel = guild.get_channel(settings.OWNER_NOTIFY_CHANNEL_ID)
        if alert_channel:
            embed = discord.Embed(
                title="🚨 누크 감지 및 대응",
                description=f"**대상**: {admin_member.mention} ({admin_member.id})\n"
                           f"**사유**: 짧은 시간 내 대량 차단 실행\n"
                           f"**제거된 역할**: {', '.join(removed_roles) if removed_roles else '없음'}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="⚠️ 주의사항",
                value="관리자 권한이 자동으로 회수되었습니다.\n"
                      "의도된 행동이었다면 권한을 다시 부여해 주세요.",
                inline=False
            )
            
            await alert_channel.send(embed=embed)
    
    async def _log_member_ban(self, guild: discord.Guild, user: discord.User):
        """차단 로그 기록"""
        log_channel = guild.get_channel(settings.LOG_CHANNEL_ID)
        if not log_channel:
            return
        
        # 감사 로그에서 정보 가져오기
        reason = "사유 없음"
        moderator = None
        
        async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            if entry.target.id == user.id:
                reason = entry.reason or "사유 없음"
                moderator = entry.user
                break
        
        embed = discord.Embed(
            title="🔨 멤버 차단",
            description=f"**대상**: {user.mention} ({user.id})\n"
                       f"**실행자**: {moderator.mention if moderator else '알 수 없음'}\n"
                       f"**사유**: {reason}",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        await log_channel.send(embed=embed)
    
    # ============== 차단 해제 관련 이벤트 ==============
    
    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """멤버 차단 해제 시 처리"""
        try:
            if guild.id != settings.USING_SERVER_ID:
                return
            
            # 차단 해제 로그 기록
            await self._log_member_unban(guild, user)
            
        except Exception as e:
            self.bot.logger.error(f"Error in on_member_unban: {e}", exc_info=True)
    
    async def _log_member_unban(self, guild: discord.Guild, user: discord.User):
        """차단 해제 로그 기록"""
        log_channel = guild.get_channel(settings.LOG_CHANNEL_ID)
        if not log_channel:
            return
        
        # 감사 로그에서 정보 가져오기
        reason = "사유 없음"
        moderator = None
        
        async for entry in guild.audit_logs(action=discord.AuditLogAction.unban, limit=1):
            if entry.target.id == user.id:
                reason = entry.reason or "사유 없음"
                moderator = entry.user
                break
        
        embed = discord.Embed(
            title="🔓 멤버 차단 해제",
            description=f"**대상**: {user.mention} ({user.id})\n"
                       f"**실행자**: {moderator.mention if moderator else '알 수 없음'}\n"
                       f"**사유**: {reason}",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        await log_channel.send(embed=embed)
    
    # ============== 기타 조치 관련 이벤트 ==============
    
    @commands.Cog.listener()
    async def on_member_kick(self, guild: discord.Guild, user: discord.User):
        """멤버 추방 시 처리 (직접적인 이벤트는 없지만 감사 로그로 감지)"""
        # Discord.py에는 직접적인 kick 이벤트가 없으므로
        # 감사 로그를 주기적으로 확인하거나 다른 방식으로 구현
        pass
    
    async def check_recent_kicks(self, guild: discord.Guild):
        """최근 추방 확인 (주기적 호출용)"""
        try:
            async for entry in guild.audit_logs(
                action=discord.AuditLogAction.kick,
                limit=5,
                after=datetime.utcnow() - timedelta(minutes=1)
            ):
                await self._log_member_kick(guild, entry.target, entry.user, entry.reason)
        except Exception as e:
            self.bot.logger.error(f"Error checking recent kicks: {e}")
    
    async def _log_member_kick(self, guild: discord.Guild, user: discord.User, 
                             moderator: discord.User, reason: str):
        """추방 로그 기록"""
        log_channel = guild.get_channel(settings.LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="👢 멤버 추방",
                description=f"**대상**: {user.mention} ({user.id})\n"
                           f"**실행자**: {moderator.mention}\n"
                           f"**사유**: {reason or '사유 없음'}",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            await log_channel.send(embed=embed)


async def setup(bot):
    """Cog 설정"""
    await bot.add_cog(ModerationEvents(bot))