"""Embeddings via Voyage AI (modelo jurídico voyage-law-2, 1024 dims)."""
import httpx

from app.config import get_settings

VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"


async def embed(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """Gera embeddings. input_type: 'document' ao indexar, 'query' ao buscar."""
    s = get_settings()
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            VOYAGE_URL,
            headers={"Authorization": f"Bearer {s.VOYAGE_API_KEY}"},
            json={"input": texts, "model": s.VOYAGE_MODEL, "input_type": input_type},
        )
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]


async def embed_one(text: str, input_type: str = "document") -> list[float]:
    return (await embed([text], input_type))[0]
