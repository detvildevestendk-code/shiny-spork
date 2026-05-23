from functools import lru_cache
from typing import Literal

from pydantic import Field, PositiveFloat, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "AI Futures Bot"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://bot:bot_password@postgres:5432/futures_bot"
    redis_url: str = "redis://redis:6379/0"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    ai_filter_enabled: bool = True
    ai_min_confidence: float = Field(default=0.62, ge=0, le=1)

    exchange_name: Literal["bybit", "binance"] = "bybit"
    bybit_api_key: str | None = None
    bybit_api_secret: str | None = None
    binance_api_key: str | None = None
    binance_api_secret: str | None = None
    exchange_sandbox: bool = True
    hedge_mode_enabled: bool = True

    max_leverage: PositiveInt = 10
    default_leverage: PositiveInt = 3
    max_open_trades: PositiveInt = 5
    max_daily_loss_pct: PositiveFloat = 3.0
    max_position_risk_pct: PositiveFloat = 1.0
    max_account_exposure_pct: PositiveFloat = 40.0
    losing_streak_cooldown_minutes: PositiveInt = 45
    extreme_volatility_threshold_pct: PositiveFloat = 8.0

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
