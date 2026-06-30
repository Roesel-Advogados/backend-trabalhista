"""Pacote por template (custo zero): substab + carta de preposição + juntada."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.services import templates_service
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/templates", tags=["templates"])


class DadosProcesso(BaseModel):
    processo_id: str | None = None
    numero_processo: str | None = None
    reclamada: str | None = None
    cnpj: str | None = None
    comarca: str | None = None
    vara: str | None = None
    advogado_substabelecente: str | None = None
    oab_substabelecente: str | None = None
    advogado_substabelecido: str | None = None
    oab_substabelecido: str | None = None
    preposto: str | None = None
    cpf_preposto: str | None = None


@router.post("/pacote")
async def gerar_pacote(dados: DadosProcesso):
    pacote = templates_service.gerar_pacote(dados.model_dump(exclude_none=True))

    if dados.processo_id:
        sb = get_supabase()
        sb.table("pecas").insert(
            [
                {
                    "processo_id": dados.processo_id,
                    "tipo": tipo,
                    "conteudo": conteudo,
                    "modelo_usado": "template",
                    "custo_usd": 0,
                }
                for tipo, conteudo in pacote.items()
            ]
        ).execute()

    return {"custo_usd": 0, **pacote}
