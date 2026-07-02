"""Busca semântica de defesas parecidas via embedding + pgvector."""
from app.services.gemini_service import embed_one
from app.supabase_client import get_supabase


async def buscar_defesas_parecidas(
    texto_inicial: str, k: int = 3, tipo: str | None = "contestacao"
) -> list[dict]:
    """Embeda a inicial e busca as k defesas mais similares via RPC pgvector."""
    query_emb = await embed_one(texto_inicial, input_type="query")
    sb = get_supabase()
    resp = sb.rpc(
        "match_defesas",
        {"query_embedding": query_emb, "match_count": k, "filtro_tipo": tipo},
    ).execute()
    return resp.data or []