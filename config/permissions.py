"""
GarlicBot Permission Configuration

This module contains permission-related configurations and checks.
"""

from typing import List, Dict, Optional
import discord


class PermissionConfig:
    """Permission configuration and validation class"""
    
    def __init__(self):
        self._load_permission_levels()
        self._load_command_permissions()
    
    def _load_permission_levels(self):
        """권한 레벨 정의"""
        self.PERMISSION_LEVELS = {
            "OWNER": 5,
            "SUPER_ADMIN": 4, 
            "ADMIN": 3,
            "MODERATOR": 2,
            "TRUSTED": 1,
            "USER": 0
        }
    
    def _load_command_permissions(self):
        """명령어별 필요 권한 정의"""
        self.COMMAND_PERMISSIONS = {
            # 관리자 전용 명령어
            "종료": "OWNER",
            "다시시작": "OWNER", 
            "권한회수": "SUPER_ADMIN",
            "일괄차단": "ADMIN",
            "일괄차단해제": "ADMIN",
            "모든역할회수": "ADMIN",
            "보안점검": "ADMIN",
            
            # 조치 관련 명령어
            "경고": "MODERATOR",
            "경고차감": "MODERATOR",
            "추방": "MODERATOR",
            "차단": "MODERATOR",
            "차단해제": "MODERATOR",
            "타임아웃": "MODERATOR",
            "타임아웃해제": "MODERATOR",
            
            # 서버 관리 명령어
            "슬로우모드": "MODERATOR",
            "스레드일괄처리": "MODERATOR",
            "로그채널설정": "ADMIN",
            "경고한도설정": "ADMIN",
            
            # 일반 사용자 명령어
            "출석체크": "USER",
            "경험치확인": "USER",
            "경험치선물": "USER",
            "경험치도박": "USER",
            "골라": "USER",
            "추천받기": "USER",
            "날씨": "USER",
            "핑": "USER",
            "타임스탬프": "USER",
            "서버정보": "USER",
            "사용자정보": "USER"
        }
    
    def check_permission(self, user: discord.Member, required_level: str) -> bool:
        """사용자의 권한을 확인합니다."""
        user_level = self.get_user_permission_level(user)
        required_level_value = self.PERMISSION_LEVELS.get(required_level, 0)
        user_level_value = self.PERMISSION_LEVELS.get(user_level, 0)
        
        return user_level_value >= required_level_value
    
    def get_user_permission_level(self, user: discord.Member) -> str:
        """사용자의 권한 레벨을 반환합니다."""
        from config.settings import settings
        
        # 소유자 체크
        if user.id in settings.OWNERS or user.id == user.guild.owner_id:
            return "OWNER"
        
        # 최고 관리자 체크
        if user.id in settings.SUPER_ADMINS:
            return "SUPER_ADMIN"
        
        # 관리자 체크
        if user.id in settings.ADMINS:
            return "ADMIN"
        
        # Discord 권한 기반 체크
        if user.guild_permissions.administrator:
            return "ADMIN"
        
        if (user.guild_permissions.ban_members or 
            user.guild_permissions.kick_members or
            user.guild_permissions.moderate_members):
            return "MODERATOR"
        
        # 신뢰 역할 체크
        trusted_role = user.guild.get_role(settings.TRUST_ROLE_ID)
        if trusted_role and trusted_role in user.roles:
            return "TRUSTED"
        
        return "USER"
    
    def has_discord_permission(self, user: discord.Member, permission: str) -> bool:
        """Discord 권한을 체크합니다."""
        return getattr(user.guild_permissions, permission, False)
    
    def can_use_command(self, user: discord.Member, command_name: str) -> bool:
        """사용자가 특정 명령어를 사용할 수 있는지 확인합니다."""
        required_level = self.COMMAND_PERMISSIONS.get(command_name, "USER")
        return self.check_permission(user, required_level)
    
    def get_missing_permissions(self, user: discord.Member, required_perms: List[str]) -> List[str]:
        """사용자가 가지지 않은 권한 목록을 반환합니다."""
        missing = []
        for perm in required_perms:
            if not self.has_discord_permission(user, perm):
                missing.append(perm)
        return missing


# 글로벌 권한 설정 인스턴스
permissions = PermissionConfig()