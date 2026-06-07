"""
Centralized Configuration
Use pydantic-settings for validated Environment Variables
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field
from functools import lru_cache

class Settings(BaseSettings):

    # LLM Configuration
    GEMINI_API_KEY: str
    PRIMARY_MODEL: str = "gemini-3.1-flash-lite"
    FALLBACK_MODEL: str = "gemini-3.1-flash-lite"

    # LangChain API
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_PROJECT: str = "production-api"

    # App Config
    APP_NAME: str = "Production LangGraph API"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    RATE_LIMIT: str = "20/minute"
    CACHE_TTL_SECONDS: int = 300
    MAX_RETRIES: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance - loaded once, reused everywhere"""
    return Settings()

settings = get_settings()

import os

os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
os.environ["LANGCHAIN_TRACING_V2"] = str(settings.LANGCHAIN_TRACING_V2).lower()
os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT

os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY
