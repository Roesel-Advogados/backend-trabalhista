"""Listagem e atualização de status das peças."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/pecas", tags=["pecas"])


@router.get("")
async def listar():
    sb = get_supabase()
    resp = (
        sb.table("pecas")
        .select("id, processo_id, tipo, status, modelo_usado, custo_usd, created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data


@router.get("/{peca_id}")
async def detalhe(peca_id: str):
    sb = get_supabase()
    resp = sb.table("pecas").select("*").eq("id", peca_id).single().execute()
    return resp.data


class StatusUpdate(BaseModel):
    status: str  # rascunho | revisado | protocolado


@router.patch("/{peca_id}")
async def atualizar_status(peca_id: str, body: StatusUpdate):
    sb = get_supabase()
    resp = (
        sb.table("pecas").update({"status": body.status}).eq("id", peca_id).execute()
    )
    return resp.data
