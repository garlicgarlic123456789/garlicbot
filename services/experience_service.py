"""
GarlicBot Experience Service

경험치 및 레벨 시스템을 담당하는 서비스 클래스입니다.
- 경험치 획득 및 관리
- 레벨 계산 및 레벨업 처리
- 경험치 설정 관리
- 경험치 통계 및 랭킹
"""

import discord
from typing import Optional, List, Dict, Any, Tuple
import asyncio
import logging
from datetime import datetime, timedelta
import json
import random

from config import settings
from core.exceptions import GarlicBotException
from utils.helpers import calculate_level_from_exp, format_number


class ExperienceService:
    """경험치 시스템을 담당하는 클래스"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 경험치 설정 캐시
        self.xp_settings_cache = {}
        
        # 최근 경험치 획득 추적 (스팸 방지)
        self.recent_xp_gains = {}
        
        # 경험치 획득 기본값
        self.default_xp_range = (15, 25)
        self.xp_cooldown = 60  # 60초 쿨다운
    
    # ============== 경험치 관리 ==============
    
    async def add_experience(self, user_id: int, guild_id: int, 
                           amount: Optional[int] = None, 
                           source: str = "message") -> Dict[str, Any]:
        """
        사용자에게 경험치를 추가합니다
        
        Args:
            user_id: 사용자 ID
            guild_id: 서버 ID
            amount: 추가할 경험치 (None이면 랜덤)
            source: 경험치 획득 소스
        
        Returns:
            경험치 추가 결과 (레벨업 정보 포함)
        """
        try:
            # 경험치 설정 확인
            xp_settings = await self.get_xp_settings(guild_id)
            if not xp_settings.get('enabled', True):
                return {'success': False, 'reason': 'XP system disabled'}
            
            # 쿨다운 검사
            if not await self._check_xp_cooldown(user_id, guild_id):
                return {'success': False, 'reason': 'Cooldown active'}
            
            # 경험치 양 결정
            if amount is None:
                min_xp, max_xp = self.default_xp_range
                amount = random.randint(min_xp, max_xp)
            
            # 현재 경험치 가져오기
            current_exp = await self.get_user_experience(user_id, guild_id)
            current_level = calculate_level_from_exp(current_exp)
            
            # 경험치 추가
            new_exp = current_exp + amount
            new_level = calculate_level_from_exp(new_exp)
            
            # 데이터베이스 업데이트
            await self._update_user_experience(user_id, guild_id, new_exp)
            
            # 쿨다운 설정
            await self._set_xp_cooldown(user_id, guild_id)
            
            # 레벨업 확인
            level_up = new_level > current_level
            
            result = {
                'success': True,
                'exp_gained': amount,
                'total_exp': new_exp,
                'current_level': new_level,
                'level_up': level_up,
                'source': source
            }
            
            if level_up:
                result['previous_level'] = current_level
                result['level_difference'] = new_level - current_level
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error adding experience: {e}")
            return {'success': False, 'reason': str(e)}
    
    async def get_user_experience(self, user_id: int, guild_id: int) -> int:
        """
        사용자의 경험치를 가져옵니다
        
        Args:
            user_id: 사용자 ID
            guild_id: 서버 ID
        
        Returns:
            사용자의 총 경험치
        """
        try:
            async with self.bot.db.acquire() as conn:
                cursor = await conn.execute("""
                    SELECT exp FROM exp WHERE user_id = ? AND server_id = ?
                """, (user_id, guild_id))
                row = await cursor.fetchone()
                
                return row[0] if row else 0
                
        except Exception as e:
            self.logger.error(f"Error getting user experience: {e}")
            return 0
    
    async def get_user_level(self, user_id: int, guild_id: int) -> int:
        """
        사용자의 레벨을 가져옵니다
        
        Args:
            user_id: 사용자 ID
            guild_id: 서버 ID
        
        Returns:
            사용자의 현재 레벨
        """
        exp = await self.get_user_experience(user_id, guild_id)
        return calculate_level_from_exp(exp)
    
    async def set_user_experience(self, user_id: int, guild_id: int, 
                                exp: int, moderator_id: Optional[int] = None) -> bool:
        """
        사용자의 경험치를 설정합니다
        
        Args:
            user_id: 사용자 ID
            guild_id: 서버 ID
            exp: 설정할 경험치
            moderator_id: 설정한 관리자 ID
        
        Returns:
            성공 여부
        """
        try:
            await self._update_user_experience(user_id, guild_id, exp)
            
            # 로그 기록
            if moderator_id:
                self.logger.info(
                    f"Experience set by moderator {moderator_id}: "
                    f"User {user_id} in guild {guild_id} -> {exp} XP"
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting user experience: {e}")
            return False
    
    # ============== 랭킹 시스템 ==============
    
    async def get_leaderboard(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        서버 경험치 랭킹을 가져옵니다
        
        Args:
            guild_id: 서버 ID
            limit: 가져올 랭킹 수
        
        Returns:
            랭킹 리스트
        """
        try:
            async with self.bot.db.acquire() as conn:
                cursor = await conn.execute("""
                    SELECT user_id, exp FROM exp 
                    WHERE server_id = ? 
                    ORDER BY exp DESC 
                    LIMIT ?
                """, (guild_id, limit))
                rows = await cursor.fetchall()
                
                leaderboard = []
                for rank, (user_id, exp) in enumerate(rows, 1):
                    level = calculate_level_from_exp(exp)
                    leaderboard.append({
                        'rank': rank,
                        'user_id': user_id,
                        'exp': exp,
                        'level': level
                    })
                
                return leaderboard
                
        except Exception as e:
            self.logger.error(f"Error getting leaderboard: {e}")
            return []
    
    async def get_user_rank(self, user_id: int, guild_id: int) -> Optional[int]:
        """
        사용자의 서버 내 랭킹을 가져옵니다
        
        Args:
            user_id: 사용자 ID
            guild_id: 서버 ID
        
        Returns:
            사용자 랭킹 (없으면 None)
        """
        try:
            async with self.bot.db.acquire() as conn:
                cursor = await conn.execute("""
                    SELECT COUNT(*) + 1 as rank FROM exp 
                    WHERE server_id = ? AND exp > (
                        SELECT COALESCE(exp, 0) FROM exp 
                        WHERE user_id = ? AND server_id = ?
                    )
                """, (guild_id, user_id, guild_id))
                row = await cursor.fetchone()
                
                # 사용자가 경험치를 가지고 있는지 확인
                user_exp = await self.get_user_experience(user_id, guild_id)
                if user_exp == 0:
                    return None
                
                return row[0] if row else None
                
        except Exception as e:
            self.logger.error(f"Error getting user rank: {e}")
            return None
    
    # ============== 경험치 설정 관리 ==============
    
    async def get_xp_settings(self, guild_id: int) -> Dict[str, Any]:
        """
        서버의 경험치 설정을 가져옵니다
        
        Args:
            guild_id: 서버 ID
        
        Returns:
            경험치 설정 딕셔너리
        """
        try:
            # 캐시 확인
            if guild_id in self.xp_settings_cache:
                return self.xp_settings_cache[guild_id]
            
            async with self.bot.db.acquire() as conn:
                cursor = await conn.execute("""
                    SELECT enabled, min_xp, max_xp, cooldown, level_up_message
                    FROM xp_settings WHERE guild_id = ?
                """, (guild_id,))
                row = await cursor.fetchone()
                
                if row:
                    settings = {
                        'enabled': bool(row[0]),
                        'min_xp': row[1],
                        'max_xp': row[2],
                        'cooldown': row[3],
                        'level_up_message': bool(row[4])
                    }
                else:
                    # 기본 설정
                    settings = {
                        'enabled': True,
                        'min_xp': 15,
                        'max_xp': 25,
                        'cooldown': 60,
                        'level_up_message': True
                    }
                
                # 캐시에 저장
                self.xp_settings_cache[guild_id] = settings
                return settings
                
        except Exception as e:
            self.logger.error(f"Error getting XP settings: {e}")
            return {
                'enabled': True,
                'min_xp': 15,
                'max_xp': 25,
                'cooldown': 60,
                'level_up_message': True
            }
    
    async def update_xp_settings(self, guild_id: int, settings: Dict[str, Any]) -> bool:
        """
        서버의 경험치 설정을 업데이트합니다
        
        Args:
            guild_id: 서버 ID
            settings: 새로운 설정 딕셔너리
        
        Returns:
            성공 여부
        """
        try:
            async with self.bot.db.acquire() as conn:
                await conn.execute("""
                    INSERT OR REPLACE INTO xp_settings 
                    (guild_id, enabled, min_xp, max_xp, cooldown, level_up_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    guild_id,
                    settings.get('enabled', True),
                    settings.get('min_xp', 15),
                    settings.get('max_xp', 25),
                    settings.get('cooldown', 60),
                    settings.get('level_up_message', True)
                ))
                await conn.commit()
            
            # 캐시 업데이트
            self.xp_settings_cache[guild_id] = settings
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating XP settings: {e}")
            return False
    
    # ============== 레벨업 처리 ==============
    
    async def handle_level_up(self, user_id: int, guild_id: int, 
                            new_level: int, previous_level: int,
                            channel: discord.TextChannel) -> bool:
        """
        레벨업을 처리합니다
        
        Args:
            user_id: 사용자 ID
            guild_id: 서버 ID
            new_level: 새로운 레벨
            previous_level: 이전 레벨
            channel: 메시지를 보낼 채널
        
        Returns:
            성공 여부
        """
        try:
            # 설정 확인
            xp_settings = await self.get_xp_settings(guild_id)
            if not xp_settings.get('level_up_message', True):
                return True
            
            # 사용자 정보 가져오기
            user = self.bot.get_user(user_id)
            if not user:
                return False
            
            # 레벨업 메시지 전송
            embed = discord.Embed(
                title="🎉 레벨업!",
                description=f"{user.mention}님이 **레벨 {new_level}**에 도달했습니다!",
                color=discord.Color.gold(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="이전 레벨",
                value=str(previous_level),
                inline=True
            )
            
            embed.add_field(
                name="현재 레벨", 
                value=str(new_level),
                inline=True
            )
            
            embed.add_field(
                name="레벨 차이",
                value=f"+{new_level - previous_level}",
                inline=True
            )
            
            embed.set_thumbnail(url=user.display_avatar.url)
            
            await channel.send(embed=embed)
            
            # 레벨업 보상 처리
            await self._handle_level_rewards(user_id, guild_id, new_level)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling level up: {e}")
            return False
    
    # ============== 경험치 통계 ==============
    
    async def get_guild_xp_stats(self, guild_id: int) -> Dict[str, Any]:
        """
        서버의 경험치 통계를 가져옵니다
        
        Args:
            guild_id: 서버 ID
        
        Returns:
            통계 딕셔너리
        """
        try:
            async with self.bot.db.acquire() as conn:
                # 전체 통계
                cursor = await conn.execute("""
                    SELECT 
                        COUNT(*) as total_users,
                        SUM(exp) as total_exp,
                        AVG(exp) as avg_exp,
                        MAX(exp) as max_exp
                    FROM exp WHERE server_id = ? AND exp > 0
                """, (guild_id,))
                stats_row = await cursor.fetchone()
                
                # 레벨별 분포
                cursor = await conn.execute("""
                    SELECT exp FROM exp WHERE server_id = ? AND exp > 0
                """, (guild_id,))
                exp_rows = await cursor.fetchall()
                
                level_distribution = {}
                for (exp,) in exp_rows:
                    level = calculate_level_from_exp(exp)
                    level_distribution[level] = level_distribution.get(level, 0) + 1
                
                return {
                    'total_users': stats_row[0] if stats_row[0] else 0,
                    'total_exp': stats_row[1] if stats_row[1] else 0,
                    'avg_exp': round(stats_row[2], 2) if stats_row[2] else 0,
                    'max_exp': stats_row[3] if stats_row[3] else 0,
                    'level_distribution': level_distribution
                }
                
        except Exception as e:
            self.logger.error(f"Error getting guild XP stats: {e}")
            return {}
    
    # ============== 내부 헬퍼 메서드 ==============
    
    async def _update_user_experience(self, user_id: int, guild_id: int, exp: int):
        """사용자 경험치 업데이트"""
        async with self.bot.db.acquire() as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO exp (user_id, server_id, exp)
                VALUES (?, ?, ?)
            """, (user_id, guild_id, exp))
            await conn.commit()
    
    async def _check_xp_cooldown(self, user_id: int, guild_id: int) -> bool:
        """경험치 획득 쿨다운 확인"""
        try:
            key = f"{guild_id}:{user_id}"
            current_time = datetime.utcnow()
            
            if key in self.recent_xp_gains:
                last_gain = self.recent_xp_gains[key]
                if (current_time - last_gain).total_seconds() < self.xp_cooldown:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking XP cooldown: {e}")
            return True
    
    async def _set_xp_cooldown(self, user_id: int, guild_id: int):
        """경험치 획득 쿨다운 설정"""
        try:
            key = f"{guild_id}:{user_id}"
            self.recent_xp_gains[key] = datetime.utcnow()
            
            # 정리: 1시간 이상 된 항목들 제거
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            keys_to_remove = [
                k for k, v in self.recent_xp_gains.items() 
                if v < cutoff_time
            ]
            
            for key in keys_to_remove:
                del self.recent_xp_gains[key]
                
        except Exception as e:
            self.logger.error(f"Error setting XP cooldown: {e}")
    
    async def _handle_level_rewards(self, user_id: int, guild_id: int, level: int):
        """레벨업 보상 처리"""
        try:
            # 특정 레벨에서 보상 지급
            rewards_config = {
                5: "초보자 역할",
                10: "활동적인 멤버 역할", 
                20: "열정적인 멤버 역할",
                50: "베테랑 멤버 역할"
            }
            
            if level in rewards_config:
                self.logger.info(
                    f"Level reward available for user {user_id} at level {level}: "
                    f"{rewards_config[level]}"
                )
                # 실제 보상 지급 로직은 여기에 구현
                
        except Exception as e:
            self.logger.error(f"Error handling level rewards: {e}")
    
    # ============== 유틸리티 메서드 ==============
    
    def calculate_exp_for_level(self, target_level: int) -> int:
        """
        특정 레벨에 도달하기 위해 필요한 경험치를 계산합니다
        
        Args:
            target_level: 목표 레벨
        
        Returns:
            필요한 경험치
        """
        # 레벨별 필요 경험치 (역계산)
        level_requirements = {
            1: 0, 2: 150, 3: 300, 4: 500, 5: 1000,
            6: 1500, 7: 2000, 8: 2700, 9: 3700, 10: 5000,
            11: 6500, 12: 8200, 13: 10500, 14: 13000, 15: 15700,
            16: 18700, 17: 22000, 18: 27000, 19: 33000, 20: 40000,
            21: 48000, 22: 57000, 23: 67000, 24: 79000, 25: 93000,
            26: 109000, 27: 127000, 28: 150000, 29: 180000, 30: 220000,
            31: 270000, 32: 350000, 33: 500000
        }
        
        return level_requirements.get(target_level, 500000)
    
    def get_next_level_progress(self, current_exp: int) -> Dict[str, Any]:
        """
        다음 레벨까지의 진행도를 계산합니다
        
        Args:
            current_exp: 현재 경험치
        
        Returns:
            진행도 정보
        """
        current_level = calculate_level_from_exp(current_exp)
        next_level = current_level + 1
        
        current_level_exp = self.calculate_exp_for_level(current_level)
        next_level_exp = self.calculate_exp_for_level(next_level)
        
        exp_in_level = current_exp - current_level_exp
        exp_needed = next_level_exp - current_level_exp
        
        progress_percentage = (exp_in_level / exp_needed) * 100 if exp_needed > 0 else 100
        
        return {
            'current_level': current_level,
            'next_level': next_level,
            'exp_in_level': exp_in_level,
            'exp_needed_for_next': exp_needed - exp_in_level,
            'progress_percentage': round(progress_percentage, 1)
        }