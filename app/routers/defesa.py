"""Geração da contestação a partir da petição inicial."""
from fastapi import APIRouter, File, UploadFile

from app.services import generate
from app.services.anthropic_service import gerar
from app.services.extract import extrair
from app.services.search import buscar_defesas_parecidas
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/defesa", tags=["defesa"])


@router.post("/gerar")
async def gerar_defesa(file: UploadFile = File(...)):
    # 1. extrai texto da inicial
    data = await file.read()
    inicial = extrair(file.filename, data)

    # 2. busca defesas parecidas na memória jurídica
    refs = await buscar_defesas_parecidas(inicial, k=3, tipo="contestacao")

    # 3. gera contestação com Claude
    res = await gerar(
        system=generate.SYSTEM_CONTESTACAO,
        prompt=generate.prompt_contestacao(inicial, refs),
    )

    # 4. persiste processo + peça
    sb = get_supabase()
    proc = sb.table("processos").insert({"inicial_texto": inicial}).execute()
    processo_id = proc.data[0]["id"]
    peca = (
        sb.table("pecas")
        .insert(
            {
                "processo_id": processo_id,
                "tipo": "contestacao",
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
        "referencias_usadas": [
            {"titulo": r["titulo"], "similaridade": r["similaridade"]} for r in refs
        ],
    }
