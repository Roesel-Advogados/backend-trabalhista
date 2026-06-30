"""Cliente Supabase (service role — ignora RLS, uso server-side apenas)."""
from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


@lru_cache
def get_supabase() -> Client:
    s = get_settings()
    if not s.SUPABASE_URL or not s.SUPABASE_SERVICE_KEY:
        raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_KEY são obrigatórios.")
    return create_client(s.SUPABASE_URL, s.SUPABASE_SERVICE_KEY)
