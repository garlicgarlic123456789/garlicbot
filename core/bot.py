"""
GarlicBot Core Bot Class

This module contains the main bot class and initialization logic.
"""

import discord
from discord.ext import commands
import asyncio
import logging
from typing import Optional, List
import os

from config import settings, constants
from core.exceptions import GarlicBotException


class GarlicBot(commands.Bot):
    """Main GarlicBot class extending discord.py Bot"""
    
    def __init__(self):
        # Discord Intents 설정
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.reactions = True
        intents.voice_states = True
        intents.presences = True
        
        # Bot 초기화
        super().__init__(
            command_prefix="!",  # 기본 prefix (슬래시 명령어 위주 사용)
            intents=intents,
            help_command=None,  # 기본 help 명령어 비활성화
            case_insensitive=True,
            owner_ids=set(settings.OWNERS)
        )
        
        # 로깅 설정
        self.setup_logging()
        
        # 봇 상태 변수
        self.is_ready = False
        self.start_time = None
        
        # 캐시 및 저장소
        self.guild_settings = {}
        self.user_data = {}
        
        # 외부 클라이언트들
        self.openai_client = None
        self.weather_client = None
        
        # 서비스 인스턴스들
        self.ai_service = None
        self.moderation_service = None
        self.experience_service = None
        
        self.logger.info("GarlicBot instance created")
    
    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('bot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def setup_hook(self):
        """Bot 시작 시 실행되는 설정"""
        self.logger.info("Setting up bot...")
        
        # 데이터베이스 초기화
        from core.database import DatabaseManager
        self.db = DatabaseManager()
        await self.db.initialize()
        
        # 외부 클라이언트 초기화
        await self.setup_external_clients()
        
        # 서비스 초기화
        await self.setup_services()
        
        # 명령어 로드
        await self.load_commands()
        
        # 이벤트 핸들러 로드  
        await self.load_events()
        
        # 백그라운드 태스크 시작
        await self.start_background_tasks()
        
        self.logger.info("Bot setup complete")
    
    async def setup_external_clients(self):
        """외부 API 클라이언트 설정"""
        try:
            # OpenAI 클라이언트
            if settings.GEMENI_API_KEY:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMENI_API_KEY)
                self.logger.info("Google AI client initialized")
            
            # AsyncOpenAI 클라이언트
            from openai import AsyncOpenAI
            self.openai_client = AsyncOpenAI()
            self.logger.info("OpenAI client initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize external clients: {e}")
    
    async def setup_services(self):
        """서비스 인스턴스 초기화"""
        try:
            from services.ai_service import AIService
            from services.moderation_service import ModerationService
            from services.experience_service import ExperienceService
            
            self.ai_service = AIService(self)
            self.moderation_service = ModerationService(self)
            self.experience_service = ExperienceService(self)
            
            self.logger.info("Services initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
    
    async def load_commands(self):
        """명령어 모듈 로드"""
        command_modules = [
            "commands.experience",
            "commands.moderation", 
            "commands.utility",
            "commands.admin"
        ]
        
        for module in command_modules:
            try:
                await self.load_extension(module)
                self.logger.info(f"Loaded command module: {module}")
            except Exception as e:
                self.logger.error(f"Failed to load command module {module}: {e}")
    
    async def load_events(self):
        """이벤트 핸들러 로드"""
        event_modules = [
            "events.message",
            "events.member",
            "events.moderation", 
            "events.guild"
        ]
        
        for module in event_modules:
            try:
                await self.load_extension(module)
                self.logger.info(f"Loaded event module: {module}")
            except Exception as e:
                self.logger.error(f"Failed to load event module {module}: {e}")
    
    async def start_background_tasks(self):
        """백그라운드 태스크 시작"""
        # 경험치 정기 백업
        # 메시지 로그 정리
        # 기타 주기적 작업들
        pass
    
    async def on_ready(self):
        """Bot이 준비되었을 때"""
        if not self.is_ready:
            self.is_ready = True
            self.start_time = discord.utils.utcnow()
            
            self.logger.info(f'{self.user} has connected to Discord!')
            self.logger.info(f'Bot is in {len(self.guilds)} guilds')
            
            # 봇 상태 설정
            await self.change_presence(
                activity=discord.Game(name="마늘봇 2.0 | /도움말"),
                status=discord.Status.online
            )
    
    async def on_disconnect(self):
        """Bot 연결이 끊어졌을 때"""
        self.logger.warning("Bot disconnected from Discord")
    
    async def on_resumed(self):
        """Bot 연결이 재개되었을 때"""
        self.logger.info("Bot connection resumed")
    
    async def close(self):
        """Bot 종료 시 정리"""
        self.logger.info("Shutting down bot...")
        
        # 데이터베이스 연결 종료
        if hasattr(self, 'db'):
            await self.db.close()
        
        # 부모 클래스의 close 호출
        await super().close()
        
        self.logger.info("Bot shutdown complete")
    
    async def get_guild_settings(self, guild_id: int) -> dict:
        """서버별 설정 가져오기"""
        if guild_id not in self.guild_settings:
            # 데이터베이스에서 설정 로드
            self.guild_settings[guild_id] = await self.db.get_guild_settings(guild_id)
        return self.guild_settings[guild_id]
    
    async def update_guild_settings(self, guild_id: int, settings: dict):
        """서버별 설정 업데이트"""
        self.guild_settings[guild_id] = settings
        await self.db.update_guild_settings(guild_id, settings)
    
    def run_bot(self):
        """Bot 실행"""
        try:
            self.run(settings.DISCORD_TOKEN, log_handler=None)
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            raise GarlicBotException(f"Bot startup failed: {e}")


# 전역 봇 인스턴스  
bot = None

def get_bot() -> GarlicBot:
    """전역 봇 인스턴스 반환"""
    global bot
    if bot is None:
        bot = GarlicBot()
    return bot