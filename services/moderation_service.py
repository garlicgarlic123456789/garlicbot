"""
GarlicBot Moderation Service

조치 및 관리 관련 기능을 담당하는 서비스 클래스입니다.
- 타임아웃/차단/추방 관리
- 안티 레이드 시스템
- 안티 누크 시스템
- 자동 조치 및 로깅
"""

import discord
from discord.ext import commands
from typing import Optional, List, Dict, Any, Union
import asyncio
import logging
from datetime import datetime, timedelta
import json

from config import settings, constants
from core.exceptions import GarlicBotException

# 위험한 권한 목록
DANGEROUS_PERMISSIONS = [
    'ban_members', 'kick_members', 'manage_channels',
    'manage_guild', 'manage_roles', 'administrator'
]
from utils.helpers import format_duration, format_timestamp


class ModerationService:
    """조치 관련 서비스를 담당하는 클래스"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 안티 레이드 추적
        self.recent_joins = {}
        
        # 안티 누크 추적
        self.ban_time_tracking = {}
        self.role_creation_tracking = {}
        
        # 타임아웃 추적
        self.timeout_tracking = {}
    
    # ============== 기본 조치 기능 ==============
    
    async def timeout_user(self, member: discord.Member, duration: timedelta,
                         reason: str = None, moderator: discord.Member = None,
                         ignore_ongoing: bool = False) -> bool:
        """
        사용자에게 타임아웃을 부여합니다
        
        Args:
            member: 타임아웃할 멤버
            duration: 타임아웃 지속 시간
            reason: 타임아웃 사유
            moderator: 조치를 실행한 관리자
            ignore_ongoing: 기존 타임아웃 무시 여부
        
        Returns:
            성공 여부
        """
        try:
            if ignore_ongoing:
                new_timeout = discord.utils.utcnow() + duration
            else:
                if member.timed_out_until and member.timed_out_until > discord.utils.utcnow():
                    # 기존 타임아웃 시간에 추가
                    new_timeout = member.timed_out_until + duration
                else:
                    # 현재 시간에서 타임아웃 시간 계산
                    new_timeout = discord.utils.utcnow() + duration
            
            await member.edit(timed_out_until=new_timeout, reason=reason)
            
            # 로그 기록
            await self._log_timeout(member, duration, reason, moderator)
            
            return True
            
        except discord.Forbidden:
            self.logger.error(f"Failed to timeout {member}: Missing permissions")
            return False
        except Exception as e:
            self.logger.error(f"Error timing out user {member}: {e}")
            return False
    
    async def remove_timeout(self, member: discord.Member, 
                           reason: str = None, moderator: discord.Member = None) -> bool:
        """
        사용자의 타임아웃을 해제합니다
        
        Args:
            member: 타임아웃을 해제할 멤버
            reason: 해제 사유
            moderator: 조치를 실행한 관리자
        
        Returns:
            성공 여부
        """
        try:
            await member.edit(timed_out_until=None, reason=reason)
            
            # 로그 기록
            await self._log_timeout_removal(member, reason, moderator)
            
            return True
            
        except discord.Forbidden:
            self.logger.error(f"Failed to remove timeout from {member}: Missing permissions")
            return False
        except Exception as e:
            self.logger.error(f"Error removing timeout from {member}: {e}")
            return False
    
    async def ban_user(self, guild: discord.Guild, user: Union[discord.Member, discord.User],
                      reason: str = None, moderator: discord.Member = None,
                      delete_message_days: int = 0) -> bool:
        """
        사용자를 차단합니다
        
        Args:
            guild: 서버
            user: 차단할 사용자
            reason: 차단 사유
            moderator: 조치를 실행한 관리자
            delete_message_days: 삭제할 메시지 일수
        
        Returns:
            성공 여부
        """
        try:
            await guild.ban(
                user, 
                reason=reason, 
                delete_message_days=delete_message_days
            )
            
            # 로그 기록
            await self._log_ban(guild, user, reason, moderator)
            
            return True
            
        except discord.Forbidden:
            self.logger.error(f"Failed to ban {user}: Missing permissions")
            return False
        except Exception as e:
            self.logger.error(f"Error banning user {user}: {e}")
            return False
    
    async def unban_user(self, guild: discord.Guild, user: discord.User,
                        reason: str = None, moderator: discord.Member = None) -> bool:
        """
        사용자의 차단을 해제합니다
        
        Args:
            guild: 서버
            user: 차단 해제할 사용자
            reason: 해제 사유
            moderator: 조치를 실행한 관리자
        
        Returns:
            성공 여부
        """
        try:
            await guild.unban(user, reason=reason)
            
            # 로그 기록
            await self._log_unban(guild, user, reason, moderator)
            
            return True
            
        except discord.Forbidden:
            self.logger.error(f"Failed to unban {user}: Missing permissions")
            return False
        except discord.NotFound:
            self.logger.error(f"User {user} is not banned")
            return False
        except Exception as e:
            self.logger.error(f"Error unbanning user {user}: {e}")
            return False
    
    async def kick_user(self, member: discord.Member,
                       reason: str = None, moderator: discord.Member = None) -> bool:
        """
        사용자를 추방합니다
        
        Args:
            member: 추방할 멤버
            reason: 추방 사유
            moderator: 조치를 실행한 관리자
        
        Returns:
            성공 여부
        """
        try:
            await member.kick(reason=reason)
            
            # 로그 기록
            await self._log_kick(member, reason, moderator)
            
            return True
            
        except discord.Forbidden:
            self.logger.error(f"Failed to kick {member}: Missing permissions")
            return False
        except Exception as e:
            self.logger.error(f"Error kicking user {member}: {e}")
            return False
    
    # ============== 안티 레이드 시스템 ==============
    
    async def check_raid_protection(self, member: discord.Member) -> Dict[str, Any]:
        """
        레이드 방어 검사를 수행합니다
        
        Args:
            member: 입장한 멤버
        
        Returns:
            레이드 검사 결과
        """
        try:
            guild_id = member.guild.id
            current_time = datetime.utcnow()
            
            # 안티 레이드 설정 확인
            raid_settings = await self._get_anti_raid_settings(guild_id)
            if not raid_settings or not raid_settings.get('on_off', False):
                return {'is_raid': False, 'action': None}
            
            # 최근 가입자 추적
            if guild_id not in self.recent_joins:
                self.recent_joins[guild_id] = []
            
            # 현재 시간 추가
            self.recent_joins[guild_id].append(current_time)
            
            # 설정된 시간 이전의 가입자만 유지
            duration_seconds = raid_settings.get('duration', 60)
            cutoff_time = current_time - timedelta(seconds=duration_seconds)
            
            self.recent_joins[guild_id] = [
                join_time for join_time in self.recent_joins[guild_id]
                if join_time > cutoff_time
            ]
            
            # 레이드 판단
            join_threshold = raid_settings.get('join_time', 5)
            recent_joins_count = len(self.recent_joins[guild_id])
            
            if recent_joins_count >= join_threshold:
                return {
                    'is_raid': True,
                    'action': raid_settings.get('action', 'kick'),
                    'recent_joins': recent_joins_count,
                    'threshold': join_threshold
                }
            
            return {'is_raid': False, 'action': None}
            
        except Exception as e:
            self.logger.error(f"Error checking raid protection: {e}")
            return {'is_raid': False, 'action': None}
    
    async def execute_raid_action(self, member: discord.Member, action: str) -> bool:
        """
        레이드 방어 조치를 실행합니다
        
        Args:
            member: 대상 멤버
            action: 실행할 조치 ('kick', 'ban', 'timeout')
        
        Returns:
            성공 여부
        """
        try:
            reason = "안티 레이드: 의심스러운 대량 가입 감지"
            
            if action == 'kick':
                return await self.kick_user(member, reason=reason)
            elif action == 'ban':
                return await self.ban_user(member.guild, member, reason=reason)
            elif action == 'timeout':
                timeout_duration = timedelta(hours=1)  # 1시간 타임아웃
                return await self.timeout_user(member, timeout_duration, reason=reason)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error executing raid action: {e}")
            return False
    
    # ============== 안티 누크 시스템 ==============
    
    async def check_anti_nuke_ban(self, guild: discord.Guild, banned_user: discord.User,
                                moderator: discord.Member) -> bool:
        """
        안티 누크 차단 검사를 수행합니다
        
        Args:
            guild: 서버
            banned_user: 차단된 사용자
            moderator: 차단을 실행한 관리자
        
        Returns:
            누크 감지 여부
        """
        try:
            # 화이트리스트 체크
            if await self._is_whitelisted(moderator):
                return False
            
            guild_id = guild.id
            moderator_id = moderator.id
            current_time = datetime.utcnow()
            
            # 서버별 차단 시간 추적
            if guild_id not in self.ban_time_tracking:
                self.ban_time_tracking[guild_id] = {}
            
            if moderator_id not in self.ban_time_tracking[guild_id]:
                self.ban_time_tracking[guild_id][moderator_id] = []
            
            # 현재 시간 추가
            self.ban_time_tracking[guild_id][moderator_id].append(current_time)
            
            # 10분 이내의 차단만 유지
            cutoff_time = current_time - timedelta(minutes=10)
            self.ban_time_tracking[guild_id][moderator_id] = [
                ban_time for ban_time in self.ban_time_tracking[guild_id][moderator_id]
                if ban_time > cutoff_time
            ]
            
            # 차단 횟수 확인
            ban_count = len(self.ban_time_tracking[guild_id][moderator_id])
            
            if ban_count > settings.BAN_NUKE_COUNT:
                # 누크 감지 - 권한 회수
                await self._handle_nuke_detection(moderator, 'ban')
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking anti-nuke ban: {e}")
            return False
    
    async def check_anti_nuke_role_creation(self, role: discord.Role, 
                                          creator: discord.Member) -> bool:
        """
        안티 누크 역할 생성 검사를 수행합니다
        
        Args:
            role: 생성된 역할
            creator: 역할을 생성한 사용자
        
        Returns:
            누크 감지 여부
        """
        try:
            # 화이트리스트 체크
            if await self._is_whitelisted(creator):
                return False
            
            guild_id = role.guild.id
            creator_id = creator.id
            current_time = datetime.utcnow()
            
            # 역할 생성 추적
            if guild_id not in self.role_creation_tracking:
                self.role_creation_tracking[guild_id] = {}
            
            if creator_id not in self.role_creation_tracking[guild_id]:
                self.role_creation_tracking[guild_id][creator_id] = []
            
            # 현재 시간 추가
            self.role_creation_tracking[guild_id][creator_id].append(current_time)
            
            # 5분 이내 생성만 유지
            cutoff_time = current_time - timedelta(minutes=5)
            self.role_creation_tracking[guild_id][creator_id] = [
                create_time for create_time in self.role_creation_tracking[guild_id][creator_id]
                if create_time > cutoff_time
            ]
            
            # 임계값 확인 (5분에 5개 이상)
            creation_count = len(self.role_creation_tracking[guild_id][creator_id])
            
            if creation_count >= 5:
                # 누크 감지 - 권한 회수
                await self._handle_nuke_detection(creator, 'role_spam')
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking anti-nuke role creation: {e}")
            return False
    
    # ============== 내부 헬퍼 메서드 ==============
    
    async def _get_anti_raid_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """안티 레이드 설정 가져오기"""
        try:
            async with self.bot.db.acquire() as conn:
                cursor = await conn.execute("""
                    SELECT on_off, action, alert_channel_id, duration, join_time
                    FROM anti_raid_settings WHERE server_id = ?
                """, (guild_id,))
                row = await cursor.fetchone()
                
                if row:
                    return {
                        'on_off': bool(row[0]),
                        'action': row[1],
                        'alert_channel_id': row[2],
                        'duration': row[3],
                        'join_time': row[4]
                    }
                return None
        except Exception as e:
            self.logger.error(f"Error getting anti-raid settings: {e}")
            return None
    
    async def _is_whitelisted(self, member: discord.Member) -> bool:
        """사용자가 안티 누크 화이트리스트에 있는지 확인"""
        try:
            whitelist_roles = [
                member.guild.get_role(role_id) 
                for role_id in settings.ANTI_NUKE_WHITELIST
            ]
            
            return any(
                role in member.roles 
                for role in whitelist_roles 
                if role is not None
            )
        except Exception as e:
            self.logger.error(f"Error checking whitelist: {e}")
            return False
    
    async def _handle_nuke_detection(self, member: discord.Member, nuke_type: str):
        """누크 감지 시 처리"""
        try:
            # 위험한 권한들 회수
            removed_roles = []
            
            for role in member.roles:
                if role == member.guild.default_role:
                    continue
                    
                # 역할의 권한 확인
                role_perms = role.permissions
                has_dangerous_perm = any(
                    getattr(role_perms, perm, False) for perm in DANGEROUS_PERMISSIONS
                )
                
                if has_dangerous_perm:
                    try:
                        await member.remove_roles(
                            role, 
                            reason=f"안티 누크: {nuke_type} 감지"
                        )
                        removed_roles.append(role.name)
                    except discord.Forbidden:
                        pass
            
            # 알림 전송
            await self._send_nuke_alert(member, nuke_type, removed_roles)
            
            self.logger.warning(
                f"Nuke detected and handled: {member} ({member.id}) - {nuke_type}"
            )
            
        except Exception as e:
            self.logger.error(f"Error handling nuke detection: {e}")
    
    async def _send_nuke_alert(self, member: discord.Member, nuke_type: str, 
                             removed_roles: List[str]):
        """누크 감지 알림 전송"""
        try:
            alert_channel = member.guild.get_channel(settings.OWNER_NOTIFY_CHANNEL_ID)
            if not alert_channel:
                return
            
            nuke_descriptions = {
                'ban': '짧은 시간 내 대량 차단 실행',
                'role_spam': '짧은 시간 내 대량 역할 생성'
            }
            
            embed = discord.Embed(
                title="🚨 누크 감지 및 대응",
                description=f"**대상**: {member.mention} ({member.id})\n"
                           f"**사유**: {nuke_descriptions.get(nuke_type, '알 수 없는 누크 패턴')}\n"
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
            
        except Exception as e:
            self.logger.error(f"Error sending nuke alert: {e}")
    
    # ============== 로깅 메서드 ==============
    
    async def _log_timeout(self, member: discord.Member, duration: timedelta,
                         reason: str, moderator: discord.Member):
        """타임아웃 로그 기록"""
        try:
            log_channel = member.guild.get_channel(settings.LOG_CHANNEL_ID)
            if not log_channel:
                return
            
            embed = discord.Embed(
                title="⏰ 멤버 타임아웃",
                description=f"**대상**: {member.mention} ({member.id})\n"
                           f"**실행자**: {moderator.mention if moderator else '시스템'}\n"
                           f"**지속시간**: {format_duration(duration)}\n"
                           f"**사유**: {reason or '사유 없음'}",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            await log_channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error logging timeout: {e}")
    
    async def _log_timeout_removal(self, member: discord.Member, 
                                 reason: str, moderator: discord.Member):
        """타임아웃 해제 로그 기록"""
        try:
            log_channel = member.guild.get_channel(settings.LOG_CHANNEL_ID)
            if not log_channel:
                return
            
            embed = discord.Embed(
                title="⏰ 타임아웃 해제",
                description=f"**대상**: {member.mention} ({member.id})\n"
                           f"**실행자**: {moderator.mention if moderator else '시스템'}\n"
                           f"**사유**: {reason or '사유 없음'}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            await log_channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error logging timeout removal: {e}")
    
    async def _log_ban(self, guild: discord.Guild, user: Union[discord.Member, discord.User],
                      reason: str, moderator: discord.Member):
        """차단 로그 기록"""
        try:
            log_channel = guild.get_channel(settings.LOG_CHANNEL_ID)
            if not log_channel:
                return
            
            embed = discord.Embed(
                title="🔨 멤버 차단",
                description=f"**대상**: {user.mention} ({user.id})\n"
                           f"**실행자**: {moderator.mention if moderator else '시스템'}\n"
                           f"**사유**: {reason or '사유 없음'}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            
            embed.set_thumbnail(url=user.display_avatar.url)
            await log_channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error logging ban: {e}")
    
    async def _log_unban(self, guild: discord.Guild, user: discord.User,
                        reason: str, moderator: discord.Member):
        """차단 해제 로그 기록"""
        try:
            log_channel = guild.get_channel(settings.LOG_CHANNEL_ID)
            if not log_channel:
                return
            
            embed = discord.Embed(
                title="🔓 멤버 차단 해제",
                description=f"**대상**: {user.mention} ({user.id})\n"
                           f"**실행자**: {moderator.mention if moderator else '시스템'}\n"
                           f"**사유**: {reason or '사유 없음'}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.set_thumbnail(url=user.display_avatar.url)
            await log_channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error logging unban: {e}")
    
    async def _log_kick(self, member: discord.Member, reason: str, moderator: discord.Member):
        """추방 로그 기록"""
        try:
            log_channel = member.guild.get_channel(settings.LOG_CHANNEL_ID)
            if not log_channel:
                return
            
            embed = discord.Embed(
                title="👢 멤버 추방",
                description=f"**대상**: {member.mention} ({member.id})\n"
                           f"**실행자**: {moderator.mention if moderator else '시스템'}\n"
                           f"**사유**: {reason or '사유 없음'}",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            await log_channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error logging kick: {e}")