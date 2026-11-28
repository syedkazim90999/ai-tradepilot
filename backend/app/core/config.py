"""
AI TradePilot backend — core configuration.
All secrets come from environment variables. Never commit a real .env.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI TradePilot"
    environment: str = "development"
    debug: bool = False

    # Database (PostgreSQL is the deployment target; SQLite only for local verification)
    database_url: str = "sqlite+aiosqlite:///./tradepilot.db"

    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "CHANGE_ME_dev_only_do_not_use_in_production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Fernet key for encrypting Binance API keys (generate via scripts/generate_fernet_key.py)
    fernet_key: str = ""

    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # Binance — LIVE production is the default. Testnet is not offered.
    binance_testnet_base_url: str = "https://testnet.binancefuture.com"
    binance_testnet_ws_url: str = "wss://stream.binancefuture.com"
    binance_prod_base_url: str = "https://fapi.binance.com"
    binance_prod_ws_url: str = "wss://fstream.binance.com"
    binance_use_testnet: bool = False

    # Trading defaults
    risk_per_trade_pct: float = 0.5
    daily_loss_limit_pct: float = 2.0
    max_positions: int = 5
    max_leverage: int = 20
    reward_risk_ratio: float = 2.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
