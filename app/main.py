"""DefesaAI — API FastAPI."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import defesa, memoria, pecas, recurso, templates

settings = get_settings()

app = FastAPI(title="DefesaAI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN] if settings.FRONTEND_ORIGIN != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(defesa.router)
app.include_router(recurso.router)
app.include_router(templates.router)
app.include_router(memoria.router)
app.include_router(pecas.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "defesaai"}
