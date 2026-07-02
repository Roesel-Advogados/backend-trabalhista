"""Embeddings via Google Gemini (gemini-embedding-001, 1024 dims, free tier)."""
import math

import httpx

from app.config import get_settings

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"

_TASK_TYPE = {
    "document": "RETRIEVAL_DOCUMENT",
    "query": "RETRIEVAL_QUERY",
}


def _normalize(vec: list[float]) -> list[float]:
    """Gemini não normaliza sozinho quando a dimensão != 3072."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


async def embed(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """Gera embeddings. input_type: 'document' ao indexar, 'query' ao buscar."""
    s = get_settings()
    task_type = _TASK_TYPE.get(input_type, "RETRIEVAL_DOCUMENT")
    url = GEMINI_URL.format(model=s.GEMINI_EMBEDDING_MODEL)

    resultados = []
    async with httpx.AsyncClient(timeout=60) as client:
        for texto in texts:
            resp = await client.post(
                url,
                params={"key": s.GEMINI_API_KEY},
                json={
                    "content": {"parts": [{"text": texto}]},
                    "task_type": task_type,
                    "output_dimensionality": 1024,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            vetor = data["embedding"]["values"]
            resultados.append(_normalize(vetor))
    return resultados


async def embed_one(text: str, input_type: str = "document") -> list[float]:
    return (await embed([text], input_type))[0]