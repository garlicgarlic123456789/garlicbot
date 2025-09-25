"""
GarlicBot Database Manager

This module handles all database operations for the GarlicBot.
"""

import sqlite3
import asyncio
import aiosqlite
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import logging

from config import settings
from core.exceptions import DatabaseError


class DatabaseManager:
    """Database manager for GarlicBot"""
    
    def __init__(self):
        self.db_path = "garlicbot.db"
        self.connection = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def initialize(self):
        """데이터베이스 초기화"""
        try:
            self.connection = await aiosqlite.connect(self.db_path)
            await self._create_tables()
            await self._migrate_existing_data()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise DatabaseError(f"Failed to initialize database: {e}")
    
    async def _create_tables(self):
        """테이블 생성"""
        tables = [
            # 사용자 테이블
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                display_name TEXT,
                experience INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                last_exp_time TIMESTAMP,
                warnings INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # 서버 설정 테이블
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                settings TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # 경고 로그 테이블
            """
            CREATE TABLE IF NOT EXISTS warning_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                warning_type TEXT,
                reason TEXT,
                amount INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # 조치 로그 테이블
            """
            CREATE TABLE IF NOT EXISTS moderation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                action_type TEXT,
                reason TEXT,
                duration INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # 문구 테이블 (기존 데이터 호환)
            """
            CREATE TABLE IF NOT EXISTS phrases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                type TEXT,
                server_id INTEGER,
                user_id INTEGER,
                phrase TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # 경험치 로그 테이블
            """
            CREATE TABLE IF NOT EXISTS exp_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                exp_change INTEGER,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # 반응 좋아요 테이블
            """
            CREATE TABLE IF NOT EXISTS likeability (
                user_id INTEGER PRIMARY KEY,
                points INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # 레이드 방지 설정 테이블
            """
            CREATE TABLE IF NOT EXISTS anti_raid_settings (
                server_id INTEGER PRIMARY KEY,
                enabled BOOLEAN DEFAULT 0,
                action TEXT DEFAULT 'alert',
                alert_channel_id INTEGER,
                duration INTEGER DEFAULT 180,
                join_time INTEGER DEFAULT 5,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # XP 설정 테이블
            """
            CREATE TABLE IF NOT EXISTS xp_settings (
                server_id INTEGER PRIMARY KEY,
                enabled BOOLEAN DEFAULT 1,
                multiplier REAL DEFAULT 1.0,
                cooldown INTEGER DEFAULT 60,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        for table_sql in tables:
            await self.connection.execute(table_sql)
        
        await self.connection.commit()
        self.logger.info("Database tables created/verified")
    
    async def _migrate_existing_data(self):
        """기존 JSON 파일 데이터를 데이터베이스로 마이그레이션"""
        try:
            # 경험치 데이터 마이그레이션
            await self._migrate_exp_data()
            
            # 경고 데이터 마이그레이션
            await self._migrate_warning_data()
            
            # 좋아요 데이터 마이그레이션
            await self._migrate_likeability_data()
            
            self.logger.info("Data migration completed")
        except Exception as e:
            self.logger.warning(f"Data migration failed: {e}")
    
    async def _migrate_exp_data(self):
        """경험치 JSON 데이터 마이그레이션"""
        try:
            import os
            import json
            
            if os.path.exists(settings.EXP_FILE):
                with open(settings.EXP_FILE, 'r', encoding='utf-8') as f:
                    exp_data = json.load(f)
                
                for user_id, exp in exp_data.items():
                    await self.connection.execute(
                        "INSERT OR REPLACE INTO users (user_id, experience) VALUES (?, ?)",
                        (int(user_id), exp)
                    )
                
                await self.connection.commit()
                self.logger.info("Experience data migrated")
        except Exception as e:
            self.logger.warning(f"Experience data migration failed: {e}")
    
    async def _migrate_warning_data(self):
        """경고 JSON 데이터 마이그레이션"""
        try:
            import os
            import json
            
            if os.path.exists(settings.WARNINGS_FILE):
                with open(settings.WARNINGS_FILE, 'r', encoding='utf-8') as f:
                    warning_data = json.load(f)
                
                for user_id, warnings in warning_data.items():
                    await self.connection.execute(
                        "INSERT OR REPLACE INTO users (user_id, warnings) VALUES (?, ?) "
                        "ON CONFLICT(user_id) DO UPDATE SET warnings = ?",
                        (int(user_id), warnings, warnings)
                    )
                
                await self.connection.commit()
                self.logger.info("Warning data migrated")
        except Exception as e:
            self.logger.warning(f"Warning data migration failed: {e}")
    
    async def _migrate_likeability_data(self):
        """좋아요 JSON 데이터 마이그레이션"""
        try:
            import os
            import json
            
            if os.path.exists(settings.LIKEABILITY_FILE):
                with open(settings.LIKEABILITY_FILE, 'r', encoding='utf-8') as f:
                    like_data = json.load(f)
                
                for user_id, points in like_data.items():
                    await self.connection.execute(
                        "INSERT OR REPLACE INTO likeability (user_id, points) VALUES (?, ?)",
                        (int(user_id), points)
                    )
                
                await self.connection.commit()
                self.logger.info("Likeability data migrated")
        except Exception as e:
            self.logger.warning(f"Likeability data migration failed: {e}")
    
    # 사용자 관련 메서드
    async def get_user_exp(self, user_id: int) -> int:
        """사용자 경험치 조회"""
        cursor = await self.connection.execute(
            "SELECT experience FROM users WHERE user_id = ?", (user_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0
    
    async def update_user_exp(self, user_id: int, exp: int):
        """사용자 경험치 업데이트"""
        await self.connection.execute(
            "INSERT OR REPLACE INTO users (user_id, experience) VALUES (?, ?)",
            (user_id, exp)
        )
        await self.connection.commit()
    
    async def get_user_warnings(self, user_id: int) -> int:
        """사용자 경고 수 조회"""
        cursor = await self.connection.execute(
            "SELECT warnings FROM users WHERE user_id = ?", (user_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0
    
    async def update_user_warnings(self, user_id: int, warnings: int):
        """사용자 경고 수 업데이트"""
        await self.connection.execute(
            "INSERT OR REPLACE INTO users (user_id, warnings) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET warnings = ?",
            (user_id, warnings, warnings)
        )
        await self.connection.commit()
    
    # 서버 설정 관련 메서드
    async def get_guild_settings(self, guild_id: int) -> dict:
        """서버 설정 조회"""
        cursor = await self.connection.execute(
            "SELECT settings FROM guild_settings WHERE guild_id = ?", (guild_id,)
        )
        result = await cursor.fetchone()
        if result:
            return json.loads(result[0])
        return {}
    
    async def update_guild_settings(self, guild_id: int, settings: dict):
        """서버 설정 업데이트"""
        settings_json = json.dumps(settings)
        await self.connection.execute(
            "INSERT OR REPLACE INTO guild_settings (guild_id, settings, updated_at) "
            "VALUES (?, ?, CURRENT_TIMESTAMP)",
            (guild_id, settings_json)
        )
        await self.connection.commit()
    
    # 로그 관련 메서드
    async def add_warning_log(self, guild_id: int, user_id: int, moderator_id: int, 
                            warning_type: str, reason: str, amount: int = 1):
        """경고 로그 추가"""
        await self.connection.execute(
            "INSERT INTO warning_logs (guild_id, user_id, moderator_id, warning_type, reason, amount) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, user_id, moderator_id, warning_type, reason, amount)
        )
        await self.connection.commit()
    
    async def add_moderation_log(self, guild_id: int, user_id: int, moderator_id: int,
                               action_type: str, reason: str, duration: int = None):
        """조치 로그 추가"""
        await self.connection.execute(
            "INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action_type, reason, duration) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, user_id, moderator_id, action_type, reason, duration)
        )
        await self.connection.commit()
    
    async def get_exp_leaderboard(self, limit: int = 20, offset: int = 0) -> List[tuple]:
        """경험치 순위 조회"""
        cursor = await self.connection.execute(
            "SELECT user_id, experience FROM users WHERE experience > 0 "
            "ORDER BY experience DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        return await cursor.fetchall()
    
    async def close(self):
        """데이터베이스 연결 종료"""
        if self.connection:
            await self.connection.close()
            self.logger.info("Database connection closed")