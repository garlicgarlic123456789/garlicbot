"""
GarlicBot Member Events

멤버 관련 모든 이벤트를 처리하는 모듈입니다.
- on_member_join: 멤버 가입 처리
- on_member_remove: 멤버 탈퇴 처리
- on_member_update: 멤버 정보 업데이트 처리
"""

import discord
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
from typing import Optional

from config import settings, constants
from core.exceptions import GarlicBotException
from utils.helpers import format_duration


class MemberEvents(commands.Cog):
    """멤버 관련 이벤트 핸들러"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # 서비스 인스턴스 (지연 로딩)
        self._moderation_service = None
        self._experience_service = None
        
        # 레이드 추적 변수들
        self.recent_joins = {}
        self.join_timestamps = {}
    
    @property
    def moderation_service(self):
        """조치 서비스 지연 로딩"""
        if self._moderation_service is None:
            from services.moderation_service import ModerationService
            self._moderation_service = ModerationService(self.bot)
        return self._moderation_service
    
    @property
    def experience_service(self):
        """경험치 서비스 지연 로딩"""
        if self._experience_service is None:
            from services.experience_service import ExperienceService
            self._experience_service = ExperienceService(self.bot)
        return self._experience_service
    
    # ============== 멤버 가입 이벤트 ==============
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """멤버 가입 시 처리"""
        try:
            # 서버 ID 확인
            if member.guild.id != settings.USING_SERVER_ID:
                return
            
            # 레이드 방지 체크
            if await self._check_raid_protection(member):
                return
                
            # 계정 검증
            await self._verify_account(member)
            
            # 환영 메시지 전송
            await self._send_welcome_message(member)
            
            # 자동 인증 처리
            await self._handle_auto_verification(member)
            
            # 가입 로그 기록
            await self._log_member_join(member)
            
        except Exception as e:
            self.bot.logger.error(f"Error in on_member_join: {e}", exc_info=True)
    
    async def _check_raid_protection(self, member: discord.Member) -> bool:
        """레이드 방지 체크"""
        # TODO: 레이드 방지 서비스로 이동
        # 최근 가입 계정 추적
        current_time = datetime.utcnow()
        self.recent_joins[member.id] = current_time
        
        # 5분 내 가입한 계정들 체크
        recent_count = 0
        cutoff_time = current_time - timedelta(minutes=5)
        
        for join_time in self.recent_joins.values():
            if join_time > cutoff_time:
                recent_count += 1
        
        # 레이드 감지 시 처리
        if recent_count > 5:  # 임계값
            await self._handle_raid_detection(member)
            return True
            
        return False
    
    async def _handle_raid_detection(self, member: discord.Member):
        """레이드 감지 시 처리"""
        # 알림 채널에 메시지 전송
        alert_channel = member.guild.get_channel(settings.OWNER_NOTIFY_CHANNEL_ID)
        if alert_channel:
            embed = discord.Embed(
                title="🚨 레이드 감지",
                description=f"짧은 시간 내 대량 가입이 감지되었습니다.\n"
                           f"최근 가입: {member.mention} ({member.id})",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await alert_channel.send(embed=embed)
        
        # 필요시 서버 보호 조치
        # await member.guild.edit(invites_disabled=True)
    
    async def _verify_account(self, member: discord.Member):
        """계정 검증"""
        # TODO: 계정 검증 서비스로 이동
        # 계정 생성일, 아바타 유무, 이름 패턴 등 체크
        
        account_age = datetime.utcnow() - member.created_at
        is_suspicious = False
        reasons = []
        
        # 계정이 너무 새로운 경우
        if account_age.days < 7:
            is_suspicious = True
            reasons.append("계정 생성 7일 미만")
        
        # 기본 아바타인 경우
        if member.avatar is None:
            is_suspicious = True
            reasons.append("기본 아바타 사용")
        
        # 의심스러운 계정인 경우 로그 기록
        if is_suspicious:
            log_channel = member.guild.get_channel(settings.LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(
                    title="⚠️ 의심스러운 계정 가입",
                    description=f"**사용자**: {member.mention} ({member.id})\n"
                               f"**사유**: {', '.join(reasons)}\n"
                               f"**계정 생성일**: {member.created_at.strftime('%Y-%m-%d')}",
                    color=discord.Color.orange(),
                    timestamp=datetime.utcnow()
                )
                await log_channel.send(embed=embed)
    
    async def _send_welcome_message(self, member: discord.Member):
        """환영 메시지 전송"""
        welcome_channel = member.guild.get_channel(settings.GREETING_CHANNEL_ID)
        if welcome_channel:
            embed = discord.Embed(
                title="🎉 새로운 멤버가 가입했습니다!",
                description=f"{member.mention}님, {member.guild.name}에 오신 것을 환영합니다!\n\n"
                           f"📋 서버 규칙을 확인해 주세요.\n"
                           f"💬 자유롭게 대화에 참여해 보세요!",
                color=int("a5f0ff", 16),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"멤버 #{member.guild.member_count}")
            
            await welcome_channel.send(embed=embed)
    
    async def _handle_auto_verification(self, member: discord.Member):
        """자동 인증 처리"""
        # 자동 인증 제외 사용자 체크
        if member.id in settings.NO_AUTO_VERIFY:
            return
        
        # 자동 인증이 활성화된 경우
        if settings.AUTO_VERIFY:
            verify_role = member.guild.get_role(settings.VERIFY_ROLE_ID)
            if verify_role:
                await member.add_roles(verify_role, reason="자동 인증")
    
    async def _log_member_join(self, member: discord.Member):
        """가입 로그 기록"""
        log_channel = member.guild.get_channel(settings.LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="📥 멤버 가입",
                description=f"**사용자**: {member.mention} ({member.id})\n"
                           f"**계정 생성일**: {member.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                           f"**가입 시각**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await log_channel.send(embed=embed)
    
    # ============== 멤버 탈퇴 이벤트 ==============
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """멤버 탈퇴 시 처리"""
        try:
            if member.guild.id != settings.USING_SERVER_ID:
                return
                
            # 탈퇴 메시지 전송
            await self._send_goodbye_message(member)
            
            # 탈퇴 로그 기록
            await self._log_member_leave(member)
            
        except Exception as e:
            self.bot.logger.error(f"Error in on_member_remove: {e}", exc_info=True)
    
    async def _send_goodbye_message(self, member: discord.Member):
        """탈퇴 메시지 전송"""
        goodbye_channel = member.guild.get_channel(settings.BYEBYE_CHANNEL_ID)
        if goodbye_channel:
            embed = discord.Embed(
                title="👋 멤버가 탈퇴했습니다",
                description=f"**{member.display_name}**님이 서버를 떠났습니다.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"멤버 #{member.guild.member_count}")
            
            await goodbye_channel.send(embed=embed)
    
    async def _log_member_leave(self, member: discord.Member):
        """탈퇴 로그 기록"""
        log_channel = member.guild.get_channel(settings.LOG_CHANNEL_ID)
        if log_channel:
            # 역할 정보 수집
            roles = [role.name for role in member.roles if role != member.guild.default_role]
            roles_text = ", ".join(roles) if roles else "없음"
            
            embed = discord.Embed(
                title="📤 멤버 탈퇴",
                description=f"**사용자**: {member.display_name} ({member.id})\n"
                           f"**가지고 있던 역할**: {roles_text}\n"
                           f"**탈퇴 시각**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await log_channel.send(embed=embed)
    
    # ============== 멤버 업데이트 이벤트 ==============
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """멤버 정보 업데이트 시 처리"""
        try:
            if before.guild.id != settings.USING_SERVER_ID:
                return
            
            # 역할 변경 로그
            if before.roles != after.roles:
                await self._log_role_change(before, after)
            
            # 닉네임 변경 로그
            if before.display_name != after.display_name:
                await self._log_nickname_change(before, after)
                
        except Exception as e:
            self.bot.logger.error(f"Error in on_member_update: {e}", exc_info=True)
    
    async def _log_role_change(self, before: discord.Member, after: discord.Member):
        """역할 변경 로그"""
        log_channel = before.guild.get_channel(settings.LOG_CHANNEL_ID)
        if not log_channel:
            return
        
        added_roles = set(after.roles) - set(before.roles)
        removed_roles = set(before.roles) - set(after.roles)
        
        if added_roles or removed_roles:
            embed = discord.Embed(
                title="🔄 멤버 역할 변경",
                description=f"**사용자**: {after.mention} ({after.id})",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            if added_roles:
                added_names = [role.name for role in added_roles]
                embed.add_field(
                    name="➕ 추가된 역할",
                    value=", ".join(added_names),
                    inline=False
                )
            
            if removed_roles:
                removed_names = [role.name for role in removed_roles]
                embed.add_field(
                    name="➖ 제거된 역할", 
                    value=", ".join(removed_names),
                    inline=False
                )
            
            await log_channel.send(embed=embed)
    
    async def _log_nickname_change(self, before: discord.Member, after: discord.Member):
        """닉네임 변경 로그"""
        log_channel = before.guild.get_channel(settings.LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="📝 닉네임 변경",
                description=f"**사용자**: {after.mention} ({after.id})\n"
                           f"**이전**: {before.display_name}\n"
                           f"**이후**: {after.display_name}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)


async def setup(bot):
    """Cog 설정"""
    await bot.add_cog(MemberEvents(bot))