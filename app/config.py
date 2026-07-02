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

    # Google Gemini (embeddings — free tier, sem cartão)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")

    # CORS — origem do front
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "*")


@lru_cache
def get_settings() -> Settings:
    return Settings()
