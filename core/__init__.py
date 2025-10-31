"""
GarlicBot Core Package

This package contains the core functionality of the GarlicBot.
"""

__version__ = "2.0.0"
__author__ = "GarlicBot Team"

from .bot import GarlicBot
from .database import DatabaseManager
from .exceptions import GarlicBotException

__all__ = [
    "GarlicBot",
    "DatabaseManager", 
    "GarlicBotException"
]