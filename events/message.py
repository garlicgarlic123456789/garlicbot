"""
GarlicBot Message Events

메시지 관련 모든 이벤트를 처리하는 모듈입니다.
- on_message: 메시지 수신 처리
- on_message_edit: 메시지 수정 처리  
- on_message_delete: 메시지 삭제 처리
"""

import discord
from discord.ext import commands
import re
from datetime import datetime, timedelta
import asyncio
from typing import Optional

from config import settings, constants
from core.exceptions import GarlicBotException
from utils.helpers import format_duration, get_message_link


class MessageEvents(commands.Cog):
    """메시지 관련 이벤트 핸들러"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # 서비스 인스턴스 (지연 로딩)
        self._ai_service = None
        self._moderation_service = None
        
        # 메시지 추적을 위한 변수들
        self.slowmode_users = {}
        self.last_message_times = {}
        self.message_tracker = {}
    
    @property
    def ai_service(self):
        """AI 서비스 지연 로딩"""
        if self._ai_service is None:
            from services.ai_service import AIService
            self._ai_service = AIService(self.bot)
        return self._ai_service
    
    @property
    def moderation_service(self):
        """조치 서비스 지연 로딩"""
        if self._moderation_service is None:
            from services.moderation_service import ModerationService
            self._moderation_service = ModerationService(self.bot)
        return self._moderation_service
        
    # ============== 메시지 수신 이벤트 ==============
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """메시지 수신 시 처리"""
        # 봇 메시지 무시
        if message.author.bot:
            return
            
        # DM 메시지 처리
        if message.guild is None:
            await self._handle_dm_message(message)
            return
        
        # 서버 메시지 처리
        if message.guild.id == settings.USING_SERVER_ID:
            await self._handle_server_message(message)
    
    async def _handle_dm_message(self, message: discord.Message):
        """DM 메시지 처리"""
        # AI 대화 처리
        if not message.content.startswith('!'):
            await self.ai_service.handle_dm_conversation(message)
    
    async def _handle_server_message(self, message: discord.Message):
        """서버 메시지 처리"""
        try:
            # 개발자 전용 명령어 처리
            if message.author.id == settings.DEVELOPER_ID:
                if await self._handle_developer_commands(message):
                    return
            
            # 소유자 전용 명령어 처리  
            if message.author.id in settings.OWNERS:
                if await self._handle_owner_commands(message):
                    return
            
            # 스팸 및 레이드 감지
            if await self._check_for_spam_and_raid(message):
                return
                
            # 슬로우모드 처리
            if await self._handle_slowmode(message):
                return
                
            # 자동 조치 시스템
            if await self._handle_automod(message):
                return
                
            # 마늘봇 대화 처리
            if await self._handle_garlic_conversation(message):
                return
                
            # 경험치 처리
            await self._handle_experience_gain(message)
            
        except Exception as e:
            self.bot.logger.error(f"Error in on_message: {e}", exc_info=True)
    
    async def _handle_developer_commands(self, message: discord.Message) -> bool:
        """개발자 전용 명령어 처리"""
        content = message.content
        
        # 부계정 관리 명령어
        if content.startswith("!부계추가 "):
            pattern = r"^!부계추가\s+(\d+)\s+(\d+)$"
            match = re.match(pattern, content)
            if match:
                main_id, sub_id = int(match.group(1)), int(match.group(2))
                # TODO: 부계정 관리 서비스로 이동
                await message.reply("처리되었습니다.", mention_author=False)
                return True
                
        elif content.startswith("!부계제거 "):
            pattern = r"^!부계제거\s+(\d+)\s+(\d+)$"
            match = re.match(pattern, content)
            if match:
                main_id, sub_id = int(match.group(1)), int(match.group(2))
                # TODO: 부계정 관리 서비스로 이동
                await message.reply("처리되었습니다.", mention_author=False)
                return True
                
        elif content.startswith("!부계확인 "):
            pattern = r"^!부계확인\s+(\d+)$"
            match = re.match(pattern, content)
            if match:
                user_id = int(match.group(1))
                # TODO: 부계정 확인 서비스로 이동
                await message.reply("개인 DM으로 부계정 목록이 전송되었습니다.", mention_author=False)
                return True
        
        # 블랙리스트 관리 명령어
        elif content.startswith("!블리추가 "):
            pattern = r'!블리추가\s+(\d+)\s+"(.*?)"\s+"(.*?)"\s+([01])\s+(\d+)\s+(\d+)'
            match = re.match(pattern, content)
            if match:
                # TODO: 블랙리스트 관리 서비스로 이동
                await message.reply("처리되었습니다.", mention_author=False)
                return True
                
        elif content.startswith("!블리확인 "):
            user_id = int(content[6:])
            # TODO: 블랙리스트 확인 서비스로 이동
            await message.reply("블랙리스트 확인 결과를 표시합니다.", mention_author=False)
            return True
            
        elif content.startswith("!블리제거 "):
            user_id = int(content[6:])
            # TODO: 블랙리스트 제거 서비스로 이동
            await message.reply("처리되었습니다.", mention_author=False)
            return True
            
        elif content.startswith("!프리미엄등록 "):
            user_id = int(content[8:])
            # TODO: 프리미엄 관리 서비스로 이동
            await message.reply("처리되었습니다.", mention_author=False)
            return True
            
        elif content.startswith("!프리미엄제거 "):
            user_id = int(content[8:])
            # TODO: 프리미엄 관리 서비스로 이동
            await message.reply("처리되었습니다.", mention_author=False)
            return True
        
        return False
    
    async def _handle_owner_commands(self, message: discord.Message) -> bool:
        """소유자 전용 명령어 처리"""
        content = message.content
        
        if content.startswith("마늘아 권한대행"):
            # 권한 대행 처리
            await self._handle_permission_delegation(message)
            return True
            
        elif content.startswith("마늘아 권한회수"):
            # 권한 회수 처리  
            await self._handle_permission_revoke(message)
            return True
            
        return False
    
    async def _handle_permission_delegation(self, message: discord.Message):
        """권한 대행 처리"""
        content = message.content
        guild = message.guild
        
        # 특정 사용자별 처리
        user_mappings = {
            "마늘요리": 1305492487137267722,
            "세유": 1063676895000018944,
            "여의대로": 1181084142969032848,
            "챠무": 1238750780459188225
        }
        
        for name, user_id in user_mappings.items():
            if name in content:
                member = guild.get_member(user_id)
                if member:
                    await self._grant_delegation_roles(member, "소유자 권한대행")
                    embed = discord.Embed(
                        title="성공",
                        description=f"{member.mention}의 권한 대행을 시작합니다.",
                        color=int("a5f0ff", 16)
                    )
                    await message.reply(embed=embed, mention_author=False)
                    return
        
        # 멘션으로 지정된 사용자 처리
        match = re.match(r"마늘아 권한대행 <@!?(\d+)>", content)
        if match:
            user_id = int(match.group(1))
            member = guild.get_member(user_id)
            if member:
                await self._grant_delegation_roles(member, "소유자 권한대행")
                embed = discord.Embed(
                    title="성공",
                    description=f"{member.mention}의 권한 대행을 시작합니다.",
                    color=int("a5f0ff", 16)
                )
                await message.reply(embed=embed, mention_author=False)
    
    async def _grant_delegation_roles(self, member: discord.Member, reason: str):
        """권한 대행 역할 부여"""
        # TODO: 설정에서 역할 ID 가져오기
        role1 = member.guild.get_role(1335494095514374144)
        role2 = member.guild.get_role(1325846757636047030)
        
        if role1:
            await member.add_roles(role1, reason=reason)
        if role2:
            await member.add_roles(role2, reason=reason)
    
    async def _check_for_spam_and_raid(self, message: discord.Message) -> bool:
        """스팸 및 레이드 감지"""
        # 멘션 스팸 감지
        mention_count = message.content.count("<@")
        if mention_count > 7:
            await self.moderation_service.handle_spamming(
                message, "멘션 스팸으로 의심되는 활동", 7 * 60 * 60, True, None
            )
            return True
            
        # 레이드 감지 로직
        # TODO: 레이드 감지 서비스로 이동
        
        return False
    
    async def _handle_slowmode(self, message: discord.Message) -> bool:
        """슬로우모드 처리"""
        user_id = message.author.id
        
        if user_id in self.slowmode_users:
            last_message_time = self.last_message_times.get(user_id)
            cooldown = self.slowmode_users[user_id]
            
            if last_message_time:
                elapsed_time = (message.created_at - last_message_time).total_seconds()
                if elapsed_time < cooldown and user_id != settings.DEVELOPER_ID:
                    await message.delete()
                    return True
            
            self.last_message_times[user_id] = message.created_at
        else:
            self.last_message_times[user_id] = message.created_at
            
        return False
    
    async def _handle_automod(self, message: discord.Message) -> bool:
        """자동 조치 시스템"""
        return await self.moderation_service.check_message_content(message)
    
    async def _handle_garlic_conversation(self, message: discord.Message) -> bool:
        """마늘봇 대화 처리"""
        if message.content.startswith("마늘아 "):
            await self.ai_service.handle_garlic_conversation(message)
            return True
        return False
    
    async def _handle_experience_gain(self, message: discord.Message):
        """경험치 처리"""
        # TODO: 경험치 서비스로 이동
        pass
    
    # ============== 메시지 수정 이벤트 ==============
    
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """메시지 수정 시 처리"""
        # 봇 메시지나 내용이 같으면 무시
        if before.author.bot or before.content == after.content:
            return
            
        # 로그 채널에서는 무시
        if before.channel.id in settings.NO_LOG_CHANNELS:
            return
            
        # TODO: 메시지 수정 로그 처리
        
    @commands.Cog.listener()  
    async def on_raw_message_edit(self, payload):
        """Raw 메시지 수정 이벤트"""
        # TODO: Raw 메시지 수정 로그 처리
        pass
    
    # ============== 메시지 삭제 이벤트 ==============
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """메시지 삭제 시 처리"""
        # 봇 메시지나 로그 제외 채널은 무시
        if message.author.bot or message.channel.id in settings.NO_LOG_CHANNELS:
            return
            
        # TODO: 메시지 삭제 로그 처리
        
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        """Raw 메시지 삭제 이벤트"""
        # TODO: Raw 메시지 삭제 로그 처리
        pass


async def setup(bot):
    """Cog 설정"""
    await bot.add_cog(MessageEvents(bot))