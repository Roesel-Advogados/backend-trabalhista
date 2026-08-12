def _sanitizar_nome_arquivo(nome: str) -> str:
    """Remove acentos e caracteres especiais do nome do arquivo, deixando
    só letras, números, ponto, hífen e underscore — o Supabase Storage
    rejeita chaves com acentos/caracteres especiais."""
    import re
    import unicodedata
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    nome = re.sub(r"[^\w.\-]", "_", nome)
    return nome


class SignedUrlBody(BaseModel):
    filename: str
    bucket: str = "referencia"
    pasta: str = "iniciais"


@router.post("/upload-url")
async def gerar_url_upload(body: SignedUrlBody):
    """Gera uma URL assinada para o FRONTEND subir a petição inicial
    diretamente pro Supabase Storage, sem passar pelo limite de 4.5MB
    da Vercel."""
    sb = get_supabase()
    nome_limpo = _sanitizar_nome_arquivo(body.filename)
    path = f"{body.pasta}/{nome_limpo}"
    resultado = sb.storage.from_(body.bucket).create_signed_upload_url(path)
    signed_url = (
        resultado.get("signed_url")
        or resultado.get("signedURL")
        or resultado.get("url")
    )
    return {"signedUrl": signed_url, "path": path, "bucket": body.bucket}