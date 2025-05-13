"""
Configuration settings for the NBA Injury Alert system.
"""
import os
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field


class DatabaseSettings(BaseModel):
    """Database connection settings."""
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    username: str = Field(default="postgres")
    password: str = Field(default="localdev")
    database: str = Field(default="nba_injury_alert")
    
    @property
    def connection_string(self) -> str:
        """Get the database connection string."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class RedisSettings(BaseModel):
    """Redis connection settings."""
    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)
    
    @property
    def connection_string(self) -> str:
        """Get the Redis connection string."""
        return f"redis://{self.host}:{self.port}/{self.db}"


class FetcherSettings(BaseModel):
    """Settings for the NBA data fetcher."""
    poll_interval_seconds: float = Field(default=1.0)
    max_retries: int = Field(default=3)
    timeout_seconds: float = Field(default=10.0)
    nba_api_base_url: str = Field(default="https://stats.nba.com/stats")
    injury_report_endpoint: str = Field(default="/injuryreport")


class NotificationSettings(BaseModel):
    """Settings for notifications."""
    email_enabled: bool = Field(default=False)
    push_enabled: bool = Field(default=False)
    websocket_enabled: bool = Field(default=True)
    email_from_address: str = Field(default="alerts@nba-injury-alert.example.com")
    email_smtp_server: str = Field(default="smtp.example.com")
    email_smtp_port: int = Field(default=587)
    email_smtp_username: Optional[str] = Field(default=None)
    email_smtp_password: Optional[str] = Field(default=None)


class Settings(BaseModel):
    """Main application settings."""
    environment: str = Field(default="development")
    debug: bool = Field(default=True)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    fetcher: FetcherSettings = Field(default_factory=FetcherSettings)
    notification: NotificationSettings = Field(default_factory=NotificationSettings)
    top_players_source_url: str = Field(
        default="https://www.espn.com/nba/story/_/id/38387889/nba-rank-2023-24-top-100-best-players-season-predictions"
    )
    top_players_update_frequency_days: int = Field(default=30)
    
    @property
    def is_production(self) -> bool:
        """Check if the environment is production."""
        return self.environment.lower() == "production"


# Create settings instance with environment variable overrides
def get_settings() -> Settings:
    """Get application settings with environment variable overrides."""
    settings = Settings()
    
    # Override settings from environment variables
    if db_host := os.environ.get("DB_HOST"):
        settings.database.host = db_host
    
    if db_port := os.environ.get("DB_PORT"):
        settings.database.port = int(db_port)
    
    if db_user := os.environ.get("DB_USER"):
        settings.database.username = db_user
    
    if db_pass := os.environ.get("DB_PASSWORD"):
        settings.database.password = db_pass
    
    if db_name := os.environ.get("DB_NAME"):
        settings.database.database = db_name
    
    if redis_host := os.environ.get("REDIS_HOST"):
        settings.redis.host = redis_host
    
    if redis_port := os.environ.get("REDIS_PORT"):
        settings.redis.port = int(redis_port)
    
    if env := os.environ.get("ENVIRONMENT"):
        settings.environment = env
    
    if debug := os.environ.get("DEBUG"):
        settings.debug = debug.lower() in ("true", "1", "yes")
    
    return settings


# Global settings instance
settings = get_settings()
