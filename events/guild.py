"""
GarlicBot Guild Events

길드/서버 관련 모든 이벤트를 처리하는 모듈입니다.
- on_guild_join: 서버 참가 처리
- on_guild_remove: 서버 탈퇴 처리
- on_guild_update: 서버 정보 변경 처리
- on_guild_role_create: 역할 생성 처리
- on_guild_role_delete: 역할 삭제 처리
- on_guild_channel_create: 채널 생성 처리
- on_guild_channel_delete: 채널 삭제 처리
"""

import discord
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
from typing import Optional, Dict, Any

from config import settings, constants
from core.exceptions import GarlicBotException


class GuildEvents(commands.Cog):
    """길드 관련 이벤트 핸들러"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # 채널/역할 변경 추적
        self.recent_changes = {}
    
    # ============== 길드 기본 이벤트 ==============
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """봇이 서버에 참가했을 때"""
        try:
            self.bot.logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")
            
            # 길드 정보 데이터베이스에 저장
            await self._register_guild(guild)
            
            # 관리자에게 알림
            await self._notify_guild_join(guild)
            
        except Exception as e:
            self.bot.logger.error(f"Error in on_guild_join: {e}", exc_info=True)
    
    async def _register_guild(self, guild: discord.Guild):
        """길드 정보 등록"""
        async with self.bot.db.acquire() as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO guilds (guild_id, name, member_count, joined_at)
                VALUES (?, ?, ?, ?)
            """, (guild.id, guild.name, guild.member_count, datetime.utcnow().isoformat()))
            await conn.commit()
    
    async def _notify_guild_join(self, guild: discord.Guild):
        """길드 참가 알림"""
        owner_channel = self.bot.get_channel(settings.OWNER_NOTIFY_CHANNEL_ID)
        if owner_channel:
            embed = discord.Embed(
                title="🆕 새 서버 참가",
                description=f"**서버**: {guild.name}\n"
                           f"**ID**: {guild.id}\n"
                           f"**멤버 수**: {guild.member_count:,}명\n"
                           f"**소유자**: {guild.owner.mention if guild.owner else '알 수 없음'}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            
            await owner_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """봇이 서버에서 제거되었을 때"""
        try:
            self.bot.logger.info(f"Left guild: {guild.name} (ID: {guild.id})")
            
            # 길드 정보 업데이트
            await self._update_guild_left(guild)
            
            # 관리자에게 알림
            await self._notify_guild_leave(guild)
            
        except Exception as e:
            self.bot.logger.error(f"Error in on_guild_remove: {e}", exc_info=True)
    
    async def _update_guild_left(self, guild: discord.Guild):
        """길드 탈퇴 정보 업데이트"""
        async with self.bot.db.acquire() as conn:
            await conn.execute("""
                UPDATE guilds SET left_at = ? WHERE guild_id = ?
            """, (datetime.utcnow().isoformat(), guild.id))
            await conn.commit()
    
    async def _notify_guild_leave(self, guild: discord.Guild):
        """길드 탈퇴 알림"""
        owner_channel = self.bot.get_channel(settings.OWNER_NOTIFY_CHANNEL_ID)
        if owner_channel:
            embed = discord.Embed(
                title="❌ 서버 탈퇴",
                description=f"**서버**: {guild.name}\n"
                           f"**ID**: {guild.id}\n"
                           f"**멤버 수**: {guild.member_count:,}명",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            
            await owner_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        """서버 정보 변경시"""
        try:
            if after.id != settings.USING_SERVER_ID:
                return
            
            changes = []
            
            # 서버 이름 변경
            if before.name != after.name:
                changes.append(f"**이름**: {before.name} → {after.name}")
            
            # 서버 아이콘 변경
            if before.icon != after.icon:
                changes.append("**아이콘**: 변경됨")
            
            # 서버 배너 변경
            if before.banner != after.banner:
                changes.append("**배너**: 변경됨")
            
            # 소유자 변경
            if before.owner != after.owner:
                changes.append(f"**소유자**: {before.owner} → {after.owner}")
            
            if changes:
                await self._log_guild_update(after, changes)
            
        except Exception as e:
            self.bot.logger.error(f"Error in on_guild_update: {e}", exc_info=True)
    
    async def _log_guild_update(self, guild: discord.Guild, changes: list):
        """서버 변경 로그"""
        log_channel = guild.get_channel(settings.LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="⚙️ 서버 정보 변경",
                description="\n".join(changes),
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            
            await log_channel.send(embed=embed)
    
    # ============== 역할 관련 이벤트 ==============
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """역할 생성시"""
        try:
            if role.guild.id != settings.USING_SERVER_ID:
                return
            
            # 안티 누크 검사
            await self._check_role_creation_flood(role.guild, role)
            
            # 로그 기록
            await self._log_role_create(role)
            
        except Exception as e:
            self.bot.logger.error(f"Error in on_guild_role_create: {e}", exc_info=True)
    
    async def _check_role_creation_flood(self, guild: discord.Guild, role: discord.Role):
        """역할 생성 남용 검사"""
        # 감사 로그에서 생성자 확인
        async for entry in guild.audit_logs(
            action=discord.AuditLogAction.role_create,
            limit=1
        ):
            if entry.target.id == role.id:
                creator_id = entry.user.id
                
                # 화이트리스트 체크
                creator = guild.get_member(creator_id)
                if creator:
                    whitelist_roles = [guild.get_role(role_id) for role_id in settings.ANTI_NUKE_WHITELIST]
                    if any(role in creator.roles for role in whitelist_roles if role):
                        return
                
                # 최근 역할 생성 추적
                await self._track_role_creation(guild.id, creator_id)
                break
    
    async def _track_role_creation(self, guild_id: int, creator_id: int):
        """역할 생성 추적"""
        current_time = datetime.utcnow()
        
        if guild_id not in self.recent_changes:
            self.recent_changes[guild_id] = {}
        if creator_id not in self.recent_changes[guild_id]:
            self.recent_changes[guild_id][creator_id] = {'roles_created': []}
        
        # 현재 시간 추가
        self.recent_changes[guild_id][creator_id]['roles_created'].append(current_time)
        
        # 5분 이내 생성만 유지
        cutoff_time = current_time - timedelta(minutes=5)
        self.recent_changes[guild_id][creator_id]['roles_created'] = [
            time for time in self.recent_changes[guild_id][creator_id]['roles_created']
            if time > cutoff_time
        ]
        
        # 임계값 확인 (5분에 5개 이상)
        if len(self.recent_changes[guild_id][creator_id]['roles_created']) >= 5:
            guild = self.bot.get_guild(guild_id)
            if guild:
                await self._handle_role_flood(guild, creator_id)
    
    async def _handle_role_flood(self, guild: discord.Guild, creator_id: int):
        """역할 생성 남용 처리"""
        creator = guild.get_member(creator_id)
        if not creator:
            return
        
        # 역할 관리 권한 제거
        removed_roles = []
        for role in creator.roles:
            if role.permissions.manage_roles or role.permissions.administrator:
                try:
                    await creator.remove_roles(role, reason="안티 누크: 대량 역할 생성 감지")
                    removed_roles.append(role.name)
                except discord.Forbidden:
                    pass
        
        # 알림 전송
        alert_channel = guild.get_channel(settings.OWNER_NOTIFY_CHANNEL_ID)
        if alert_channel:
            embed = discord.Embed(
                title="🚨 역할 생성 남용 감지",
                description=f"**대상**: {creator.mention}\n"
                           f"**제거된 역할**: {', '.join(removed_roles) if removed_roles else '없음'}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await alert_channel.send(embed=embed)
    
    async def _log_role_create(self, role: discord.Role):
        """역할 생성 로그"""
        log_channel = role.guild.get_channel(settings.LOG_CHANNEL_ID)
        if log_channel:
            # 감사 로그에서 생성자 확인
            creator = None
            async for entry in role.guild.audit_logs(
                action=discord.AuditLogAction.role_create,
                limit=1
            ):
                if entry.target.id == role.id:
                    creator = entry.user
                    break
            
            embed = discord.Embed(
                title="🆕 역할 생성",
                description=f"**역할**: {role.mention}\n"
                           f"**생성자**: {creator.mention if creator else '알 수 없음'}\n"
                           f"**색상**: {str(role.color)}\n"
                           f"**권한**: {'관리자' if role.permissions.administrator else '일반'}",
                color=role.color if role.color != discord.Color.default() else discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """역할 삭제시"""
        try:
            if role.guild.id != settings.USING_SERVER_ID:
                return
            
            await self._log_role_delete(role)
            
        except Exception as e:
            self.bot.logger.error(f"Error in on_guild_role_delete: {e}", exc_info=True)
    
    async def _log_role_delete(self, role: discord.Role):
        """역할 삭제 로그"""
        log_channel = role.guild.get_channel(settings.LOG_CHANNEL_ID)
        if log_channel:
            # 감사 로그에서 삭제자 확인
            deleter = None
            async for entry in role.guild.audit_logs(
                action=discord.AuditLogAction.role_delete,
                limit=1
            ):
                if entry.target.id == role.id:
                    deleter = entry.user
                    break
            
            embed = discord.Embed(
                title="🗑️ 역할 삭제",
                description=f"**역할**: {role.name}\n"
                           f"**삭제자**: {deleter.mention if deleter else '알 수 없음'}\n"
                           f"**색상**: {str(role.color)}\n"
                           f"**멤버 수**: {len(role.members)}명",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            
            await log_channel.send(embed=embed)
    
    # ============== 채널 관련 이벤트 ==============
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """채널 생성시"""
        try:
            if channel.guild.id != settings.USING_SERVER_ID:
                return
            
            await self._log_channel_create(channel)
            
        except Exception as e:
            self.bot.logger.error(f"Error in on_guild_channel_create: {e}", exc_info=True)
    
    async def _log_channel_create(self, channel):
        """채널 생성 로그"""
        log_channel = channel.guild.get_channel(settings.LOG_CHANNEL_ID)
        if log_channel and channel.id != log_channel.id:  # 로그 채널 자체 제외
            # 감사 로그에서 생성자 확인
            creator = None
            async for entry in channel.guild.audit_logs(
                action=discord.AuditLogAction.channel_create,
                limit=1
            ):
                if entry.target.id == channel.id:
                    creator = entry.user
                    break
            
            channel_type = {
                discord.ChannelType.text: "텍스트 채널",
                discord.ChannelType.voice: "음성 채널",
                discord.ChannelType.category: "카테고리",
                discord.ChannelType.news: "공지 채널",
                discord.ChannelType.stage_voice: "스테이지 채널",
                discord.ChannelType.forum: "포럼 채널"
            }.get(channel.type, "알 수 없는 채널")
            
            embed = discord.Embed(
                title="📝 채널 생성",
                description=f"**채널**: {channel.mention}\n"
                           f"**유형**: {channel_type}\n"
                           f"**생성자**: {creator.mention if creator else '알 수 없음'}\n"
                           f"**카테고리**: {channel.category.name if channel.category else '없음'}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """채널 삭제시"""
        try:
            if channel.guild.id != settings.USING_SERVER_ID:
                return
            
            await self._log_channel_delete(channel)
            
        except Exception as e:
            self.bot.logger.error(f"Error in on_guild_channel_delete: {e}", exc_info=True)
    
    async def _log_channel_delete(self, channel):
        """채널 삭제 로그"""
        log_channel = channel.guild.get_channel(settings.LOG_CHANNEL_ID)
        if log_channel and channel.id != log_channel.id:  # 로그 채널 자체 제외
            # 감사 로그에서 삭제자 확인
            deleter = None
            async for entry in channel.guild.audit_logs(
                action=discord.AuditLogAction.channel_delete,
                limit=1
            ):
                if entry.target.id == channel.id:
                    deleter = entry.user
                    break
            
            channel_type = {
                discord.ChannelType.text: "텍스트 채널",
                discord.ChannelType.voice: "음성 채널",
                discord.ChannelType.category: "카테고리",
                discord.ChannelType.news: "공지 채널",
                discord.ChannelType.stage_voice: "스테이지 채널",
                discord.ChannelType.forum: "포럼 채널"
            }.get(channel.type, "알 수 없는 채널")
            
            embed = discord.Embed(
                title="🗑️ 채널 삭제",
                description=f"**채널**: #{channel.name}\n"
                           f"**유형**: {channel_type}\n"
                           f"**삭제자**: {deleter.mention if deleter else '알 수 없음'}\n"
                           f"**카테고리**: {channel.category.name if channel.category else '없음'}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            
            await log_channel.send(embed=embed)


async def setup(bot):
    """Cog 설정"""
    await bot.add_cog(GuildEvents(bot))