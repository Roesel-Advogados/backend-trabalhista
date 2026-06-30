"""Configurações lidas de variáveis de ambiente."""
import os
from functools import lru_cache


class Settings:
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    # Anthropic (Claude)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    # Voyage AI (embeddings jurídicos)
    VOYAGE_API_KEY: str = os.getenv("VOYAGE_API_KEY", "")
    VOYAGE_MODEL: str = os.getenv("VOYAGE_MODEL", "voyage-law-2")  # 1024 dims

    # CORS — origem do front
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "*")


@lru_cache
def get_settings() -> Settings:
    return Settings()
