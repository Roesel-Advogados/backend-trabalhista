"""Monta o DOCX no modelo do escritório Roesel Advogados.

O texto vem da IA (texto puro, às vezes com resíduos de markdown). Esta camada:
- remove/converte markdown (#, **, *, >, ---, tabelas com barras);
- aplica o template do escritório (margens 4/3/3/3 cm, logo no cabeçalho,
  rodapé de Nova Lima sem número de página, Times New Roman 11, entrelinha
  1,5, recuo de 1ª linha 1,25 cm e linha em branco entre parágrafos);
- formata títulos, citações (TNR 10, recuo de 4 cm, espaço simples),
  cabeçalho das razões, vocativo, destaques [[...]] e campos [preencher];
- quebra a página antes das razões e insere o bloco de assinaturas.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

FONT = "Times New Roman"
BODY_SIZE = 11
QUOTE_SIZE = 10
LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo-roesel.png"
FOOTER_LINES = [
    "Alameda Oscar Niemeyer, 1033 | Portaria 04 | Sala 120, Vila da Serra | "
    "Nova Lima | MG | CEP: 34.006-065",
    "(31) 3517.8805 | (31) 3517.8648",
]
# Bloco de assinaturas padrão: duas colunas e, abaixo, uma assinatura centralizada.
ASSINATURAS_LINHA_1 = [
    ("CLAUDIANE AQUINO ROESEL", "OAB/MG 158.965"),
    ("KARINA ROSALINA DE OLIVEIRA", "OAB/MG 185.392"),
]
ASSINATURAS_LINHA_2 = [("VANESSA GUIMARÃES CAIXETA", "OAB/MG 248.884")]
_SIGNER_NAMES = {n for n, _ in ASSINATURAS_LINHA_1 + ASSINATURAS_LINHA_2}

_ROMAN_HEADING = re.compile(r"^(?:[IVXLCDM]+(?:\.\d+)*)\s*[–—-]\s*\S", re.I)
_PROCESS = re.compile(r"^(PROCESSO(?:\s+N[º°o.]*)?|RECORRENTES?|RECORRID[OA]S?|ORIGEM|RECLAMANTES?|RECLAMAD[OA]S?)\s*:\s*(.*)$", re.I)
_ADDRESS = re.compile(r"^(EXCELENT[ÍI]SSIM|EGR[ÉE]GIO\s+TRIBUNAL)", re.I)
_TITLE = re.compile(r"^(RAZÕES\s+D[OE]\s+RECURSO|CONTESTAÇÃO$|RECURSO ORDINÁRIO( ADESIVO)?$|CONTRARRAZÕES)", re.I)
_VOCATIVE = re.compile(r"^(Egr[ée]gia\s+Turma|Excelent[íi]ssimos?\s+Senhores?\s+Desembargador|Colenda\s+Turma|Ínclitos?)", re.I)
_LOCAL_DATA = re.compile(r"^Nova Lima\s*/\s*MG\s*,", re.I)
_PRINT = re.compile(r"^\[INSERIR PRINT", re.I)
_SIGNATURE = re.compile(r"OAB\s*/\s*[A-Z]{2}|^_{3,}|^\[?preencher,?\s+demais patronos", re.I)
_INLINE = re.compile(r"(\[\[.+?\]\]|\[preencher[^\]]*\]|\[INSERIR PRINT[^\]]*\])", re.I)


# --------------------------------------------------------------------- utils
def _font(run, size: float = BODY_SIZE, bold: bool | None = None,
          underline: bool | None = None, highlight: bool = False) -> None:
    run.font.name = FONT
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), FONT)
    run.font.size = Pt(size)
    run.italic = False
    if bold is not None:
        run.bold = bold
    if underline is not None:
        run.underline = underline
    if highlight:
        run.font.highlight_color = WD_COLOR_INDEX.YELLOW


def _borderless(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tbl_pr.append(borders)


def _strip_markdown(line: str) -> tuple[str, str | None]:
    """Remove marcações markdown da linha e devolve (texto, dica_de_tipo)."""
    hint = None
    s = line.strip()
    if re.fullmatch(r"[-*_—–=]{3,}", s):
        return "", "rule"
    m = re.match(r"^#{1,6}\s+(.*)$", s)
    if m:
        s, hint = m.group(1), "heading"
    if s.startswith(">"):
        s, hint = s.lstrip("> ").strip(), "quote"
    m = re.match(r"^(?:[-*•]|\d+[.)])\s+(.*)$", s)
    if m and hint is None and not _ROMAN_HEADING.match(s):
        # listas viram parágrafo corrido (padrão do escritório)
        s = m.group(1) if s[0] in "-*•" else s
    # **negrito** vira destaque [[...]] se for frase inteira; senão só remove
    s = re.sub(r"\*\*(.+?)\*\*", lambda mm: f"[[{mm.group(1)}]]" if len(mm.group(1)) > 40 else mm.group(1), s)
    s = re.sub(r"__(.+?)__", r"\1", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", s)
    s = s.replace("**", "")
    # heading inteiro destacado (ex.: [[III – DO MÉRITO]]) não precisa de realce
    m = re.fullmatch(r"\[\[(.+)\]\]", s)
    if m and (hint == "heading" or _ROMAN_HEADING.match(m.group(1)) or m.group(1).isupper()):
        s = m.group(1)
    return s.strip(), hint


def _add_runs(p, text: str, size: float = BODY_SIZE, bold: bool = False,
              underline: bool = False) -> None:
    for part in _INLINE.split(text):
        if not part:
            continue
        if part.startswith("[[") and part.endswith("]]"):
            _font(p.add_run(part[2:-2]), size, bold=True, underline=True, highlight=True)
        elif part.startswith("["):
            _font(p.add_run(part), size, bold=bold, underline=underline, highlight=True)
        else:
            _font(p.add_run(part), size, bold=bold, underline=underline)


def _para(doc, text: str = "", *, align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line: float | None = 1.25,
          left: float = 0, line: float = 1.5, size: float = BODY_SIZE, bold: bool = False,
          underline: bool = False):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing = line
    pf.first_line_indent = Cm(first_line) if first_line else Cm(0)
    pf.left_indent = Cm(left)
    if text:
        _add_runs(p, text, size=size, bold=bold, underline=underline)
    return p


def _blank(doc) -> None:
    _para(doc, first_line=None)


# ------------------------------------------------------------------ template
def _configure(doc) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(BODY_SIZE)
    normal._element.get_or_add_rPr()
    normal.paragraph_format.space_after = Pt(0)

    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin, sec.bottom_margin = Cm(4.0), Cm(3.0)
    sec.left_margin, sec.right_margin = Cm(3.0), Cm(3.0)
    sec.header_distance, sec.footer_distance = Cm(1.0), Cm(1.0)

    hp = sec.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if LOGO_PATH.exists():
        hp.add_run().add_picture(str(LOGO_PATH), width=Cm(3.2))

    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.paragraph_format.space_after = Pt(0)
    fp.paragraph_format.line_spacing = 1.0
    for i, line in enumerate(FOOTER_LINES):
        if i:
            fp.add_run().add_break()
        _font(fp.add_run(line), size=8)


def _signature_cell(cell, nome: str, oab: str) -> None:
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_before = Pt(24)
    _font(p.add_run(nome), BODY_SIZE, bold=True)
    p.add_run().add_break()
    _font(p.add_run(oab), BODY_SIZE, bold=True)


def _signatures(doc) -> None:
    _blank(doc)
    t1 = doc.add_table(rows=1, cols=len(ASSINATURAS_LINHA_1))
    t1.alignment = WD_TABLE_ALIGNMENT.CENTER
    _borderless(t1)
    for cell, (nome, oab) in zip(t1.rows[0].cells, ASSINATURAS_LINHA_1):
        _signature_cell(cell, nome, oab)
    t2 = doc.add_table(rows=1, cols=1)
    t2.alignment = WD_TABLE_ALIGNMENT.CENTER
    _borderless(t2)
    _signature_cell(t2.rows[0].cells[0], *ASSINATURAS_LINHA_2[0])


def _table(doc, rows: list[list[str]]) -> None:
    ncols = max(len(r) for r in rows)
    t = doc.add_table(rows=0, cols=ncols)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for ci in range(ncols):
            txt, _ = _strip_markdown(row[ci] if ci < len(row) else "")
            p = cells[ci].paragraphs[0]
            p.paragraph_format.line_spacing = 1.0
            _add_runs(p, txt, size=QUOTE_SIZE, bold=ri == 0)
    _blank(doc)


# -------------------------------------------------------------------- parser
def _lines(conteudo: str) -> list[str]:
    return [l.rstrip() for l in (conteudo or "").replace("\r\n", "\n").split("\n")]


def gerar_docx(conteudo: str, titulo: str | None = None) -> bytes:
    """Recebe o texto da peça e devolve DOCX no padrão Roesel Advogados."""
    doc = Document()
    _configure(doc)

    lines = _lines(conteudo)
    i, started, in_quote = 0, False, False
    pending_table: list[list[str]] = []

    def flush_table():
        nonlocal pending_table
        if pending_table:
            _table(doc, pending_table)
            pending_table = []

    while i < len(lines):
        raw = lines[i].strip()
        i += 1

        # tabelas markdown → tabela Word
        if raw.startswith("|") and raw.endswith("|"):
            cells = [c.strip() for c in raw.strip("|").split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                pending_table.append(cells)
            continue
        flush_table()

        text, hint = _strip_markdown(raw)
        if not text:
            continue
        if _SIGNATURE.search(text) and len(text) < 120:
            continue  # o bloco de assinaturas é inserido pelo sistema
        nxt_txt = _strip_markdown(lines[i].strip())[0] if i < len(lines) else ""
        if text.upper() in _SIGNER_NAMES or (
            text.isupper() and len(text) < 60 and _SIGNATURE.search(nxt_txt or "")
        ):
            continue  # nome de advogado que a IA escreveu acima da OAB

        # quebra de página antes das razões
        if started and re.match(r"^EGR[ÉE]GIO\s+TRIBUNAL", text, re.I):
            doc.add_page_break()
        started = True

        m = _PROCESS.match(text)
        if _VOCATIVE.match(text):
            _para(doc, text, align=WD_ALIGN_PARAGRAPH.CENTER, first_line=None)
            if not _VOCATIVE.match(nxt_txt or "x"):
                _blank(doc)
        elif _ADDRESS.match(text):
            _para(doc, text.upper() if text.isupper() else text, align=WD_ALIGN_PARAGRAPH.CENTER if text.upper().startswith("EGR") else WD_ALIGN_PARAGRAPH.JUSTIFY,
                  first_line=None, bold=True)
            _blank(doc)
        elif m:
            p = _para(doc, first_line=None, line=1.5)
            _font(p.add_run(m.group(1).upper() + ": "), bold=True)
            _font(p.add_run(m.group(2).strip()), bold=True)
            nxt = lines[i].strip() if i < len(lines) else ""
            if not _PROCESS.match(_strip_markdown(nxt)[0] or "x:"):
                _blank(doc)
        elif _TITLE.match(text):
            _blank(doc)
            _para(doc, text.upper(), align=WD_ALIGN_PARAGRAPH.CENTER, first_line=None,
                  bold=True, underline=True)
            _blank(doc)
        elif hint == "heading" or _ROMAN_HEADING.match(text) or (
            text.isupper() and len(text) < 160 and re.search(r"[A-ZÁÉÍÓÚÇÃÕ]{3}", text)
        ):
            text = text.replace("—", "–")
            _para(doc, text.upper(), align=WD_ALIGN_PARAGRAPH.CENTER, first_line=None, bold=True)
            _blank(doc)
        elif _PRINT.match(text):
            _para(doc, text, align=WD_ALIGN_PARAGRAPH.CENTER, first_line=None, size=QUOTE_SIZE)
            _blank(doc)
        elif hint == "quote" or text[:1] in "“\"" or in_quote:
            # citações podem ocupar várias linhas: segue até fechar as aspas
            if text[:1] in "“\"" and not re.search(r"[”\"]\s*\.?\)?\s*$", text[1:]):
                in_quote = True
            elif in_quote and re.search(r"[”\"]\s*[.)]*\s*$", text):
                in_quote = False
            _para(doc, text, first_line=None, left=4.0, line=1.0, size=QUOTE_SIZE)
            if not in_quote:
                _blank(doc)
        elif _LOCAL_DATA.match(text):
            _para(doc, text, align=WD_ALIGN_PARAGRAPH.CENTER, first_line=None)
            _signatures(doc)
            _blank(doc)
        elif re.match(r"^N[ae]stes termos|^Nesses termos|^Termos em que", text, re.I):
            _para(doc, "Nesses termos, pede deferimento.", first_line=1.25)
            _blank(doc)
        else:
            _para(doc, text.replace(" — ", ", ").replace("—", ", "))
            _blank(doc)
    flush_table()

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
