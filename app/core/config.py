"""
Configuration management using environment variables.
Load settings from .env file for easy configuration.
"""

import os
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


class LogLevel(Enum):
    """
    Valid logging levels as an enumeration.
    
    Advantages:
    1. Type safety - prevents invalid values at runtime
    2. IDE autocomplete - see available levels while coding
    3. Single source of truth - define levels once, use everywhere
    4. Easy iteration - can loop over all valid levels
    5. Better documentation - explicit enum values are self-documenting
    6. Prevents typos - invalid strings cause AttributeError instead of silent bugs
    """
    
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogConfig:
    """Logging configuration from environment variables."""
    
    LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    FILE_PATH: str = os.getenv("LOG_FILE_PATH", "logs/application.log")
    FILE_ROTATION: str = os.getenv("LOG_FILE_ROTATION", "500 MB")
    FILE_RETENTION: str = os.getenv("LOG_FILE_RETENTION", "7 days")
    FILE_COMPRESSION: str = os.getenv("LOG_FILE_COMPRESSION", "zip")
    
    @staticmethod
    def validate_level(level: str) -> str:
        """
        Validate logging level against allowed enum values.
        
        Args:
            level: Logging level string to validate
            
        Returns:
            Validated level string (uppercase)
            
        Raises:
            ValueError: If level is not in LogLevel enum
        """
        level = level.upper()
        try:
            # Check if the level exists in LogLevel enum
            LogLevel[level]
            return level
        except KeyError:
            valid_levels = ", ".join([l.value for l in LogLevel])
            raise ValueError(
                f"Invalid LOG_LEVEL '{level}'. Must be one of: {valid_levels}"
            )


class AppConfig:
    """Application configuration from environment variables."""
    
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    RELOAD: bool = os.getenv("RELOAD", "True").lower() in ("true", "1", "yes")


# Validate on import
try:
    LogConfig.validate_level(LogConfig.LEVEL)
except ValueError as e:
    raise ValueError(f"Configuration error: {e}")
