"""Importa documentos jurídicos brasileiros para o Supabase.

Uso:
  python scripts/importar_documento_juridico.py documento.json

O JSON deve conter: fonte_url, jurisdicao, ramo, tipo, identificacao, titulo,
texto_integral, url_oficial e, opcionalmente, ementa, status, datas e metadados.
O script não baixa páginas automaticamente: o conteúdo precisa vir de fonte
oficial e ser revisado antes da importação.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path

from app.services.gemini_service import embed
from app.supabase_client import get_supabase

CHUNK_CHARS = 5500


def _chunks(texto: str) -> list[tuple[str | None, str]]:
    paragrafos = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    partes: list[tuple[str | None, str]] = []
    atual = ""
    referencia: str | None = None
    for paragrafo in paragrafos:
        if len(atual) + len(paragrafo) + 2 <= CHUNK_CHARS:
            atual = f"{atual}\n\n{paragrafo}".strip()
        else:
            if atual:
                partes.append((referencia, atual))
            atual = paragrafo
            referencia = None
        achado = re.match(r"^(Art\.?\s*\d+[ºo]?|S[úu]mula\s+\d+|NR-?\d+)\b", paragrafo, re.I)
        if achado:
            referencia = achado.group(1)
    if atual:
        partes.append((referencia, atual))
    return partes


async def importar(payload: dict) -> None:
    obrigatorios = [
        "fonte_url", "jurisdicao", "ramo", "tipo", "identificacao", "titulo",
        "texto_integral", "url_oficial",
    ]
    ausentes = [campo for campo in obrigatorios if not payload.get(campo)]
    if ausentes:
        raise ValueError(f"Campos obrigatórios ausentes: {', '.join(ausentes)}")
    if payload["jurisdicao"] != "BR" or payload["ramo"] != "trabalhista":
        raise ValueError("Este importador aceita somente jurisdicao=BR e ramo=trabalhista.")

    sb = get_supabase()
    fonte = (
        sb.table("fontes_juridicas")
        .select("id")
        .eq("url_oficial", payload["fonte_url"])
        .single()
        .execute()
    )
    if not fonte.data:
        raise ValueError("Fonte não cadastrada na migração: " + payload["fonte_url"])

    texto = payload["texto_integral"].strip()
    digest = hashlib.sha256(texto.encode("utf-8")).hexdigest()
    doc_data = {
        "fonte_id": fonte.data["id"],
        "jurisdicao": "BR",
        "ramo": "trabalhista",
        "tipo": payload["tipo"],
        "identificacao": payload["identificacao"],
        "titulo": payload["titulo"],
        "ementa": payload.get("ementa"),
        "texto_integral": texto,
        "status": payload.get("status", "pendente_revisao"),
        "data_publicacao": payload.get("data_publicacao"),
        "vigencia_inicio": payload.get("vigencia_inicio"),
        "vigencia_fim": payload.get("vigencia_fim"),
        "data_verificacao": payload.get("data_verificacao"),
        "url_oficial": payload["url_oficial"],
        "hash_conteudo": digest,
        "metadados": payload.get("metadados", {}),
    }
    doc = sb.table("documentos_juridicos").upsert(
        doc_data, on_conflict="identificacao,hash_conteudo"
    ).execute()
    documento_id = doc.data[0]["id"]

    partes = _chunks(texto)
    vetores = await embed([parte[1] for parte in partes], input_type="document")
    sb.table("trechos_juridicos").delete().eq("documento_id", documento_id).execute()
    rows = [
        {
            "documento_id": documento_id,
            "ordem": ordem,
            "referencia": referencia,
            "texto": conteudo,
            "embedding": vetor,
        }
        for ordem, ((referencia, conteudo), vetor) in enumerate(zip(partes, vetores), 1)
    ]
    if rows:
        sb.table("trechos_juridicos").insert(rows).execute()
    print(json.dumps({"documento_id": documento_id, "trechos": len(rows)}, ensure_ascii=False))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python scripts/importar_documento_juridico.py documento.json")
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    asyncio.run(importar(payload))


if __name__ == "__main__":
    main()
