import io
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from docx import Document
from docx.document import Document as DocumentClass
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from pypdf import PdfReader


class ErroDocumento(ValueError):
    """Erro seguro e legível para documentos não processáveis."""


def _nome_limpo(filename: str | None) -> str:
    """Normaliza o nome sem permitir que caminhos ou query strings afetem o formato."""
    nome = (filename or "").split("?", 1)[0].split("#", 1)[0].strip()
    return nome.replace("\\", "/").rsplit("/", 1)[-1]


def _extensao(filename: str | None) -> str:
    return Path(_nome_limpo(filename)).suffix.lower()


def _normalizar_texto(texto: str) -> str:
    """Remove caracteres inválidos e conserva uma quebra de linha legível."""
    texto = texto.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    linhas = [re.sub(r"[ \t]+", " ", linha).strip() for linha in texto.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(linhas)).strip()


def _iter_blocos(parent):
    """Percorre parágrafos e tabelas DOCX na ordem em que aparecem no documento."""
    if isinstance(parent, DocumentClass):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        parent_elm = parent._element

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def _extrair_blocos_docx(parent) -> list[str]:
    partes: list[str] = []
    for bloco in _iter_blocos(parent):
        if isinstance(bloco, Paragraph):
            if bloco.text.strip():
                partes.append(bloco.text)
        else:
            for linha in bloco.rows:
                celulas = [celula.text.strip() for celula in linha.cells]
                if any(celulas):
                    partes.append(" | ".join(celulas))
    return partes


def extrair_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ErroDocumento(
                "Este PDF está protegido por senha. Remova a proteção e envie o arquivo novamente."
            )
        texto = "\n".join(page.extract_text() or "" for page in reader.pages)
    except ErroDocumento:
        raise
    except Exception as exc:
        raise ErroDocumento(
            "Não foi possível ler este PDF. Verifique se o arquivo não está corrompido."
        ) from exc

    texto = _normalizar_texto(texto)
    if not texto:
        raise ErroDocumento(
            "Este PDF não possui texto selecionável. Envie um PDF pesquisável ou faça OCR "
            "antes do upload."
        )
    return texto


def extrair_docx(data: bytes) -> str:
    try:
        doc = Document(io.BytesIO(data))
        partes = _extrair_blocos_docx(doc)

        # Cabeçalhos e rodapés também podem conter identificação das partes ou pedidos.
        for secao in doc.sections:
            for bloco in (
                secao.header,
                secao.first_page_header,
                secao.even_page_header,
                secao.footer,
                secao.first_page_footer,
                secao.even_page_footer,
            ):
                partes.extend(_extrair_blocos_docx(bloco))
    except Exception as exc:
        raise ErroDocumento(
            "Não foi possível ler este arquivo Word. Salve-o novamente como .docx e tente outra vez."
        ) from exc

    texto = _normalizar_texto("\n".join(partes))
    if not texto:
        raise ErroDocumento("Este arquivo Word está vazio ou não contém texto extraível.")
    return texto


def _extrair_doc_antigo(data: bytes) -> str:
    """Converte .doc legado somente quando LibreOffice estiver instalado no runtime."""
    conversor = shutil.which("soffice") or shutil.which("libreoffice")
    if not conversor:
        raise ErroDocumento(
            "Arquivos Word antigos (.doc) não podem ser convertidos neste ambiente. "
            "Salve o documento como .docx ou PDF e envie novamente."
        )

    with tempfile.TemporaryDirectory(prefix="trabalhista-doc-") as pasta:
        origem = Path(pasta) / "entrada.doc"
        origem.write_bytes(data)
        try:
            processo = subprocess.run(
                [
                    conversor,
                    "--headless",
                    "--convert-to",
                    "docx",
                    "--outdir",
                    pasta,
                    str(origem),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ErroDocumento(
                "O Word antigo demorou ou falhou ao converter. Salve como .docx ou PDF."
            ) from exc

        convertido = Path(pasta) / "entrada.docx"
        if processo.returncode != 0 or not convertido.exists():
            raise ErroDocumento(
                "Não foi possível converter este Word antigo. Salve-o como .docx ou PDF."
            )
        return extrair_docx(convertido.read_bytes())


def _detectar_formato(filename: str | None, data: bytes) -> str:
    """Usa a assinatura do arquivo quando o nome veio sem extensão ou está incorreto."""
    extensao = _extensao(filename)
    if data.startswith(b"%PDF-"):
        return ".pdf"

    if data.startswith(b"PK"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as arquivo_zip:
                if "word/document.xml" in arquivo_zip.namelist():
                    return ".docx"
        except zipfile.BadZipFile:
            pass

    # OLE Compound File, assinatura típica do .doc binário legado.
    if data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return ".doc"
    return extensao


def extrair(filename: str | None, data: bytes) -> str:
    if not data:
        raise ErroDocumento("O arquivo enviado está vazio.")

    formato = _detectar_formato(filename, data)
    if formato == ".pdf":
        return extrair_pdf(data)
    if formato == ".docx":
        return extrair_docx(data)
    if formato == ".doc":
        return _extrair_doc_antigo(data)
    raise ErroDocumento("Formato não suportado. Envie um arquivo PDF, DOCX ou DOC.")
