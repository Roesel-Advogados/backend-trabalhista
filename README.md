# DefesaAI — Backend (FastAPI)

API de geração de peças trabalhistas. Deploy na Vercel (serverless).

## Rodar local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # preencha as chaves
uvicorn app.main:app --reload --port 8000
```

Variáveis (`.env`): `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`.

## Deploy Vercel

Aponte o projeto para esta pasta. O `vercel.json` roteia tudo para `api/index.py` (ASGI). Configure as mesmas variáveis no painel.

## Endpoints

- `POST /api/defesa/gerar` — contestação a partir da inicial
- `POST /api/recurso/gerar` — recurso a partir da sentença
- `POST /api/templates/pacote` — substab + carta de preposição + juntada
- `POST /api/memoria/upload` — indexa defesa de referência
- `GET  /api/pecas` · `GET /api/memoria` · `GET /api/health`

## Estrutura

```
app/
  main.py            app FastAPI + CORS
  config.py          variáveis de ambiente
  supabase_client.py cliente Supabase (service role)
  routers/           defesa, recurso, templates, memoria, pecas
  services/          extract, voyage, anthropic, search, generate, templates
api/index.py         entrypoint Vercel
```

> Observação: o backend usa Supabase (Postgres + pgvector) como banco. As migrations SQL não estão incluídas neste pacote.
