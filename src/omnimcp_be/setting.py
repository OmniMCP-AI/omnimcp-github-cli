from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    GITHUB_URL: str = "https://github.com/nickclyde/duckduckgo-mcp-server"


SETTINGS = Settings()
