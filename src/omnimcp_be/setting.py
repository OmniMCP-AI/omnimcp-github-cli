from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    github_url: str = "https://github.com/nickclyde/duckduckgo-mcp-server"

SETTINGS = Settings()
