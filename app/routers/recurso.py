"""Geração do Recurso Ordinário a partir da sentença desfavorável."""
from fastapi import APIRouter, File, Form, UploadFile

from app.services import generate
from app.services.anthropic_service import gerar
from app.services.extract import extrair
from app.services.search import buscar_defesas_parecidas
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/recurso", tags=["recurso"])


@router.post("/gerar")
async def gerar_recurso(
    file: UploadFile = File(...),
    processo_id: str | None = Form(None),
):
    data = await file.read()
    sentenca = extrair(file.filename, data)

    refs = await buscar_defesas_parecidas(sentenca, k=3, tipo="recurso")
    res = await gerar(
        system=generate.SYSTEM_RECURSO,
        prompt=generate.prompt_recurso(sentenca, refs),
    )

    sb = get_supabase()
    if not processo_id:
        proc = sb.table("processos").insert({"inicial_texto": sentenca}).execute()
        processo_id = proc.data[0]["id"]

    peca = (
        sb.table("pecas")
        .insert(
            {
                "processo_id": processo_id,
                "tipo": "recurso",
                "conteudo": res["texto"],
                "modelo_usado": res["modelo"],
                "custo_usd": res["custo_usd"],
            }
        )
        .execute()
    )
    return {
        "processo_id": processo_id,
        "peca_id": peca.data[0]["id"],
        "conteudo": res["texto"],
        "custo_usd": res["custo_usd"],
    }
