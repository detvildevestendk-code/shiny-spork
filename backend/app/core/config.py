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
    api_docs_enabled: bool = False
    trading_api_key: str | None = None
    cors_allowed_origins: str = "http://localhost:5173"
    frontend_api_base_url: str = "http://localhost:8000"

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
    live_trading_enabled: bool = False
    paper_trading_enabled: bool = True
    paper_trading_equity: PositiveFloat = 10_000
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

    worker_strategy_scanning_enabled: bool = False
    strategy_scan_interval_seconds: PositiveInt = 60
    trading_symbols: str = "BTC/USDT:USDT"
    enabled_strategies: str = "ema_crossover"

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    @property
    def show_api_docs(self) -> bool:
        return self.api_docs_enabled or self.app_env == "development"

    def validate_production_settings(self) -> None:
        if self.app_env != "production":
            return

        invalid_markers = ("CHANGE_ME", "replace-with", "bot_password")
        required_values = {
            "TRADING_API_KEY": self.trading_api_key,
            "DATABASE_URL": self.database_url,
            "REDIS_URL": self.redis_url,
            "CORS_ALLOWED_ORIGINS": self.cors_allowed_origins,
            "FRONTEND_API_BASE_URL": self.frontend_api_base_url,
        }
        errors: list[str] = []
        for name, value in required_values.items():
            if not value or any(marker in value for marker in invalid_markers):
                errors.append(f"{name} must be configured with a production secret")

        if any(origin == "*" for origin in self.cors_origins):
            errors.append("CORS_ALLOWED_ORIGINS must not contain '*' in production")
        if not self.frontend_api_base_url.startswith("https://"):
            errors.append("FRONTEND_API_BASE_URL should use HTTPS in production")
        if self.show_api_docs:
            errors.append("API docs must remain disabled in production unless explicitly reviewed")
        if self.live_trading_enabled:
            errors.append("LIVE_TRADING_ENABLED must remain false for this paper-trading deployment")
        if not self.paper_trading_enabled:
            errors.append("PAPER_TRADING_ENABLED must remain true for this paper-trading deployment")
        if not self.exchange_sandbox:
            errors.append("EXCHANGE_SANDBOX must remain true for Bybit/Binance sandbox-only mode")

        if errors:
            raise RuntimeError("Invalid production configuration: " + "; ".join(errors))

    @property
    def symbol_list(self) -> list[str]:
        return [symbol.strip() for symbol in self.trading_symbols.split(",") if symbol.strip()]

    @property
    def enabled_strategy_names(self) -> list[str]:
        return [name.strip() for name in self.enabled_strategies.split(",") if name.strip()]

    @property
    def cors_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]
        for origin in ("http://81.27.108.159:5173", "http://81.27.108.159"):
            if origin not in origins:
                origins.append(origin)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
