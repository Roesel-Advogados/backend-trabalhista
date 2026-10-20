"""Geração do Recurso Ordinário a partir da sentença desfavorável."""
import re
import unicodedata
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.services import generate
from app.services.anthropic_service import gerar
from app.services.extract import ErroDocumento, extrair
from app.services.search import buscar_defesas_parecidas
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/recurso", tags=["recurso"])


def _sanitizar_nome_arquivo(nome: str) -> str:
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^\w.\-]", "_", nome)


async def _gerar_a_partir_do_texto(sentenca: str, processo_id: str | None = None):
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


@router.post("/gerar")
async def gerar_recurso(
    file: UploadFile = File(...),
    processo_id: str | None = Form(None),
):
    """Mantido para arquivos pequenos; arquivos grandes usam Storage."""
    data = await file.read()
    try:
        sentenca = extrair(file.filename, data)
    except ErroDocumento as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _gerar_a_partir_do_texto(sentenca, processo_id)


class SignedUrlBody(BaseModel):
    filename: str
    bucket: str = "referencia"
    pasta: str = "sentencas"


@router.post("/upload-url")
async def gerar_url_upload_recurso(body: SignedUrlBody):
    """Cria caminho único para upload direto do PDF grande no Storage."""
    sb = get_supabase()
    nome = _sanitizar_nome_arquivo(body.filename)
    path = f"{body.pasta}/{uuid.uuid4().hex[:8]}_{nome}"
    try:
        resultado = sb.storage.from_(body.bucket).create_signed_upload_url(path)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao gerar signed URL no Supabase Storage: {exc}",
        ) from exc
    signed_url = resultado.get("signed_url") or resultado.get("signedURL") or resultado.get("url")
    return {"signedUrl": signed_url, "path": path, "bucket": body.bucket}


class FromStorageBody(BaseModel):
    path: str
    bucket: str = "referencia"
    processo_id: str | None = None


@router.post("/gerar-from-storage")
async def gerar_recurso_from_storage(body: FromStorageBody):
    sb = get_supabase()
    try:
        data = sb.storage.from_(body.bucket).download(body.path)
        sentenca = extrair(body.path, data)
    except ErroDocumento as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao ler a sentença no Supabase Storage: {exc}",
        ) from exc
    return await _gerar_a_partir_do_texto(sentenca, body.processo_id)
