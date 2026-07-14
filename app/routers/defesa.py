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


async def _gerar_a_partir_do_texto(inicial: str):
    """Lógica central de geração: busca referências, chama o modelo,
    grava processo + peça no banco. Usada tanto pelo upload direto
    quanto pelo fluxo via Supabase Storage."""
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


@router.post("/gerar")
async def gerar_defesa(file: UploadFile = File(...)):
    """Upload direto do PDF no corpo da requisição. Só funciona para
    arquivos até ~4.5 MB (limite de payload da Vercel). Para arquivos
    maiores, use /gerar-from-storage."""
    data = await file.read()
    inicial = extrair(file.filename, data)
    return await _gerar_a_partir_do_texto(inicial)


class GerarFromStorageBody(BaseModel):
    path: str
    bucket: str = "referencia"


@router.post("/gerar-from-storage")
async def gerar_defesa_storage(body: GerarFromStorageBody):
    """Pega uma petição inicial já enviada a um bucket do Supabase Storage
    e gera a contestação. Usa isso para PDFs grandes que não cabem no
    limite de payload da Vercel (4.5 MB) — mesmo padrão usado em
    /api/memoria/upload-from-storage."""
    sb = get_supabase()
    data = sb.storage.from_(body.bucket).download(body.path)
    inicial = extrair(body.path, data)
    return await _gerar_a_partir_do_texto(inicial)


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