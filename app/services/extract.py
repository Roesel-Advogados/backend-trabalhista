"""Extração de texto de PDF e Word (.docx)."""
import io

from pypdf import PdfReader
from docx import Document


def extrair_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages).strip()


def extrair_docx(data: bytes) -> str:
    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs).strip()


def extrair(filename: str, data: bytes) -> str:
    nome = filename.lower()
    if nome.endswith(".pdf"):
        return extrair_pdf(data)
    if nome.endswith(".docx"):
        return extrair_docx(data)
    raise ValueError("Formato não suportado. Envie PDF ou DOCX.")
