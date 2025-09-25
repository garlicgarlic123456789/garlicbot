"""
GarlicBot Configuration Package

This package contains all configuration-related modules for the GarlicBot.
"""

__version__ = "2.0.0"
__author__ = "GarlicBot Team"

from .settings import Settings
from .constants import Constants
from .permissions import PermissionConfig

# 전역 설정 인스턴스
settings = Settings()
constants = Constants()
permissions = PermissionConfig()

__all__ = [
    "Settings",
    "Constants", 
    "PermissionConfig",
    "settings",
    "constants",
    "permissions"
]