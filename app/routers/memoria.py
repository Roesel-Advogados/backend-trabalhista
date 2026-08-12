"""Memória jurídica: admin envia defesas anteriores -> extrai, embeda, indexa."""
from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from app.services.extract import extrair
from app.services.gemini_service import embed_one
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/memoria", tags=["memoria"])


@router.post("/upload")
async def upload_referencia(
    file: UploadFile = File(...),
    tipo: str = Form("contestacao"),
    titulo: str | None = Form(None),
):
    data = await file.read()
    conteudo = extrair(file.filename, data)
    embedding = await embed_one(conteudo, input_type="document")

    sb = get_supabase()
    row = (
        sb.table("defesas_referencia")
        .insert(
            {
                "titulo": titulo or file.filename,
                "conteudo": conteudo,
                "tipo": tipo,
                "embedding": embedding,
            }
        )
        .execute()
    )
    return {"ok": True, "id": row.data[0]["id"], "tipo": tipo}


class UploadStorageBody(BaseModel):
    path: str
    tipo: str = "contestacao"
    titulo: str | None = None
    bucket: str = "referencia"


@router.post("/upload-from-storage")
async def upload_referencia_storage(body: UploadStorageBody):
    """Pega um arquivo já enviado ao bucket 'referencia' do Supabase Storage
    e processa (extrai texto, gera embedding, grava). Usa isso para arquivos
    grandes que não cabem no limite de payload da Vercel (4.5 MB)."""
    sb = get_supabase()
    data = sb.storage.from_(body.bucket).download(body.path)
    conteudo = extrair(body.path, data)
    embedding = await embed_one(conteudo, input_type="document")

    row = (
        sb.table("defesas_referencia")
        .insert(
            {
                "titulo": body.titulo or body.path,
                "conteudo": conteudo,
                "tipo": body.tipo,
                "embedding": embedding,
            }
        )
        .execute()
    )
    return {"ok": True, "id": row.data[0]["id"], "tipo": body.tipo}


class SignedUrlBody(BaseModel):
    filename: str
    bucket: str = "referencia"
    pasta: str = "defesas"


@router.post("/upload-url")
async def gerar_url_upload(body: SignedUrlBody):
    """Gera uma URL assinada para o FRONTEND subir o arquivo diretamente
    pro Supabase Storage, sem passar pelo limite de 4.5MB da Vercel.
    O frontend deve: 1) chamar este endpoint, 2) fazer PUT do arquivo
    na signedUrl retornada, 3) chamar /upload-from-storage com o path."""
    sb = get_supabase()
    path = f"{body.pasta}/{body.filename}"
    resultado = sb.storage.from_(body.bucket).create_signed_upload_url(path)
    signed_url = (
        resultado.get("signed_url")
        or resultado.get("signedURL")
        or resultado.get("url")
    )
    return {"signedUrl": signed_url, "path": path, "bucket": body.bucket}


@router.get("")
async def listar_referencias():
    sb = get_supabase()
    resp = (
        sb.table("defesas_referencia")
        .select("id, titulo, tipo, created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data