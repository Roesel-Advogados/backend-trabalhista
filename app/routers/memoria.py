"""Memória jurídica: admin envia defesas anteriores -> extrai, embeda, indexa."""
from fastapi import APIRouter, File, Form, UploadFile

from app.services.extract import extrair
from app.services.voyage_service import embed_one
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
