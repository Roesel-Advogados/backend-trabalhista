"""Geração de texto via Claude (Anthropic)."""
from anthropic import AsyncAnthropic, APIStatusError

from app.config import get_settings

# Preço Claude Sonnet 4.6 (USD por token) — usado p/ estimar custo por peça.
# Ajuste se a tabela de preços mudar.
PRECO_INPUT = 3.0 / 1_000_000   # USD / token de entrada
PRECO_OUTPUT = 15.0 / 1_000_000  # USD / token de saída


def _client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=get_settings().ANTHROPIC_API_KEY)


async def gerar(system: str, prompt: str, max_tokens: int = 8000) -> dict:
    """Retorna {'texto', 'custo_usd', 'modelo'}."""
    s = get_settings()
    print(f"[anthropic_service] modelo={s.ANTHROPIC_MODEL!r} max_tokens={max_tokens} "
          f"len(system)={len(system)} len(prompt)={len(prompt)}")
    try:
        msg = await _client().messages.create(
            model=s.ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
    except APIStatusError as e:
        print(f"[anthropic_service] ERRO DA ANTHROPIC: status={e.status_code} "
              f"body={e.response.text}")
        raise
    texto = "".join(b.text for b in msg.content if b.type == "text")
    custo = msg.usage.input_tokens * PRECO_INPUT + msg.usage.output_tokens * PRECO_OUTPUT
    return {"texto": texto, "custo_usd": round(custo, 4), "modelo": s.ANTHROPIC_MODEL}