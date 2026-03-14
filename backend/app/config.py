"""Application settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # App
    app_name: str = "NotePassing API"
    debug: bool = True
    secret_key: str = "change-me-in-production"
    
    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/notepassing"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Temp ID settings
    temp_id_expire_minutes: int = 10  # Total expiration time
    temp_id_buffer_minutes: int = 5   # Buffer after new ID issued
    
    # Presence settings
    boost_cooldown_minutes: int = 5


@lru_cache()
def get_settings() -> Settings:
    return Settings()
