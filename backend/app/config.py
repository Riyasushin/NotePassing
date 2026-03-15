"""Application settings."""
from pathlib import Path
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
    public_base_url: str | None = None

    # Local media upload settings
    upload_root_dir: str = "uploads"
    avatar_upload_dir: str = "uploads/avatars"
    avatar_upload_max_bytes: int = 5 * 1024 * 1024
    
    # Temp ID settings
    temp_id_expire_minutes: int = 10  # Total expiration time
    temp_id_buffer_minutes: int = 5   # Buffer after new ID issued
    
    # Presence settings
    boost_cooldown_minutes: int = 5

    @property
    def backend_root_path(self) -> Path:
        return Path(__file__).resolve().parents[1]

    @property
    def upload_root_path(self) -> Path:
        path = Path(self.upload_root_dir)
        if path.is_absolute():
            return path.resolve()
        return (self.backend_root_path / path).resolve()

    @property
    def avatar_upload_path(self) -> Path:
        path = Path(self.avatar_upload_dir)
        if path.is_absolute():
            return path.resolve()
        return (self.backend_root_path / path).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
