"""Geração de texto via Claude (Anthropic)."""
from anthropic import AsyncAnthropic, APIStatusError

from app.config import get_settings

# Preço Claude Sonnet 4.6 (USD por token) — usado p/ estimar custo por peça.
# Ajuste se a tabela de preços mudar.
PRECO_INPUT = 3.0 / 1_000_000   # USD / token de entrada
PRECO_OUTPUT = 15.0 / 1_000_000  # USD / token de saída

MAX_CONTINUACOES = 4  # nº máximo de "continue" antes de desistir (evita loop infinito/custo descontrolado)


def _client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=get_settings().ANTHROPIC_API_KEY)


async def gerar(system: str, prompt: str, max_tokens: int = 16000) -> dict:
    """Gera texto com o Claude. Se a resposta for cortada por atingir
    max_tokens, pede automaticamente para continuar de onde parou,
    até completar a peça inteira (ou até MAX_CONTINUACOES tentativas).
    Retorna {'texto', 'custo_usd', 'modelo', 'truncado'}."""
    s = get_settings()
    client = _client()

    messages = [{"role": "user", "content": prompt}]
    texto_completo = ""
    custo_total = 0.0
    truncado_no_final = False

    for tentativa in range(MAX_CONTINUACOES + 1):
        print(f"[anthropic_service] tentativa={tentativa} modelo={s.ANTHROPIC_MODEL!r} "
              f"max_tokens={max_tokens} len(system)={len(system)} "
              f"len(mensagens_acumuladas)={sum(len(str(m['content'])) for m in messages)}")

        try:
            msg = await client.messages.create(
                model=s.ANTHROPIC_MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
        except APIStatusError as e:
            print(f"[anthropic_service] ERRO DA ANTHROPIC: status={e.status_code} "
                  f"body={e.response.text}")
            raise

        pedaco = "".join(b.text for b in msg.content if b.type == "text")
        texto_completo += pedaco
        custo_total += msg.usage.input_tokens * PRECO_INPUT + msg.usage.output_tokens * PRECO_OUTPUT

        if msg.stop_reason != "max_tokens":
            truncado_no_final = False
            break

        # Foi cortado: pede continuação
        truncado_no_final = True
        print(f"[anthropic_service] resposta cortada em max_tokens, pedindo continuação "
              f"(tentativa {tentativa + 1}/{MAX_CONTINUACOES})")
        messages.append({"role": "assistant", "content": pedaco})
        messages.append({
            "role": "user",
            "content": "Continue exatamente de onde parou, sem repetir nenhum trecho já "
                       "escrito e sem reiniciar o documento, até concluir a peça inteira "
                       "(incluindo fecho e assinaturas).",
        })
    else:
        print(f"[anthropic_service] AVISO: atingiu o limite de {MAX_CONTINUACOES} "
              f"continuações e a peça ainda pode estar incompleta.")

    return {
        "texto": texto_completo,
        "custo_usd": round(custo_total, 4),
        "modelo": s.ANTHROPIC_MODEL,
        "truncado": truncado_no_final,
    }