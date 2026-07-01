"""Geração da contestação a partir da petição inicial."""
import io

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services import generate
from app.services.anthropic_service import gerar
from app.services.docx_service import gerar_docx
from app.services.extract import extrair
from app.services.search import buscar_defesas_parecidas
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/defesa", tags=["defesa"])


@router.post("/gerar")
async def gerar_defesa(file: UploadFile = File(...)):
    data = await file.read()
    inicial = extrair(file.filename, data)

    refs = await buscar_defesas_parecidas(inicial, k=3, tipo="contestacao")

    res = await gerar(
        system=generate.SYSTEM_CONTESTACAO,
        prompt=generate.prompt_contestacao(inicial, refs),
    )

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


class DocxRequest(BaseModel):
    conteudo: str
    titulo: str | None = "Contestação"


@router.post("/docx")
async def baixar_docx(body: DocxRequest):
    """Gera o .docx com timbre a partir do texto da peça."""
    dados = gerar_docx(body.conteudo, body.titulo)
    nome = (body.titulo or "peca").lower().replace(" ", "-") + ".docx"
    return StreamingResponse(
        io.BytesIO(dados),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )