"""
GarlicBot Custom Exceptions

This module contains custom exception classes for the GarlicBot.
"""


class GarlicBotException(Exception):
    """Base exception class for GarlicBot"""
    
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class ConfigurationError(GarlicBotException):
    """Configuration related errors"""
    pass


class DatabaseError(GarlicBotException):
    """Database related errors"""
    pass


class PermissionError(GarlicBotException):
    """Permission related errors"""
    pass


class ValidationError(GarlicBotException):
    """Input validation errors"""
    pass


class APIError(GarlicBotException):
    """External API related errors"""
    pass


class CommandError(GarlicBotException):
    """Command execution errors"""
    pass


class ModerationError(GarlicBotException):
    """Moderation action errors"""
    pass