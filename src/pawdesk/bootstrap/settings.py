"""Configurações tipadas por ambiente usando pydantic-settings."""

from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from pawdesk.domain.constants import (
    DEFAULT_DEFECT_WINDOW_DAYS,
    DEFAULT_LATE_ORDER_HANDOFF_BUSINESS_DAYS,
    DEFAULT_REFUND_APPROVAL_LIMIT,
    DEFAULT_REGRET_WINDOW_DAYS,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PAWDESK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "local"
    log_level: str = "INFO"

    # Persistência & Fila
    storage_backend: str = "mysql"  # "mysql" | "memory"
    mysql_dsn: str = "mysql+aiomysql://pawdesk:pawdesk@mysql:3306/pawdesk"
    adk_sessions_dsn: str = "mysql+aiomysql://pawdesk:pawdesk@mysql:3306/pawdesk_adk"
    adk_session_backend: str = "database"  # "database" | "memory"
    redis_url: str = "redis://redis:6379/0"

    # Modelos LLM
    model_router: str = "anthropic/claude-haiku-4-5"
    model_specialist: str = "anthropic/claude-sonnet-4-6"
    model_judge: str = "anthropic/claude-sonnet-4-6"

    # Canal & Helpdesk
    channel_mode: str = "console"  # "console" | "whatsapp_cloud"
    helpdesk_mode: str = "fake"  # "fake" | "http"
    helpdesk_base_url: str = "http://localhost:9000"
    helpdesk_api_token: str = "dev-helpdesk-token"

    # WhatsApp Cloud API
    whatsapp_verify_token: str = "change-me"
    whatsapp_app_secret: str = "change-me"
    whatsapp_access_token: str = "change-me"
    whatsapp_phone_number_id: str = ""
    whatsapp_api_version: str = "v21.0"

    # Segurança & Admin
    pseudonym_secret: str = "dev-pseudonym-secret-change-in-prod"
    phone_encryption_key: str = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
    admin_api_token: str = "dev-admin-token"
    helpdesk_webhook_secret: str = "dev-helpdesk-secret"

    # Políticas parametrizáveis
    regret_window_days: int = DEFAULT_REGRET_WINDOW_DAYS
    defect_window_days: int = DEFAULT_DEFECT_WINDOW_DAYS
    refund_approval_limit: Decimal = DEFAULT_REFUND_APPROVAL_LIMIT
    late_order_handoff_business_days: int = DEFAULT_LATE_ORDER_HANDOFF_BUSINESS_DAYS
    vet_channel_available: bool = True
    enable_simulator: bool = True

    # Observabilidade
    otel_endpoint: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
