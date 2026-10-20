"""Monta DOCX seguindo o padrão editorial dos modelos do escritório.

O texto continua sendo produzido pela IA, mas a saída passa por uma camada
estrutural que diferencia endereçamento, identificação do processo, títulos,
subtítulos, citações, listas, fecho e assinaturas. O rodapé reproduz o
rodapé institucional observado nos modelos enviados pelo escritório.
"""
from __future__ import annotations

import io
import re
from typing import Iterable

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = "Times New Roman"
FOOTER_TEXT = (
    "Alameda Oscar Niemeyer, 1033 | Portaria 04 | Sala 120, Vila da Serra | "
    "Nova Lima | MG | CEP: 34.006-065\n(31) 3517.8805 | (31) 3517.8648"
)

_ROMAN_HEADING = re.compile(r"^\s*(?:[IVXLCDM]+|[IVXLCDM]+\.\d+)\s*[–—-]\s*.+$", re.I)
_SUBHEADING = re.compile(r"^\s*(?:[IVXLCDM]+\.\d+|\d+\.\d+)\s*[–—-]\s*.+$", re.I)
_PROCESS = re.compile(r"^\s*(?:PROCESSO|PROCESSO Nº|RECORRENTE|RECORRIDO|ORIGEM)\s*:?", re.I)
_ADDRESS = re.compile(r"^\s*EXCELENT[ÍI]SSIMO|^\s*EGR[ÉE]GIO", re.I)
_QUOTE = re.compile(r"^\s*(?:[“\"]|Art\.?\s+\d+|S[úu]mula\s+\d+)")
_LIST = re.compile(r"^\s*(?:[a-z]\)|[0-9]+[.)]|[-–—•✓])\s+", re.I)


def _set_cell_borderless(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + edge
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "nil")


def _add_page_number(paragraph) -> None:
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char1)
    run._r.append(instr)
    run._r.append(fld_char2)


def _set_run_font(run, size: float = 12, bold: bool | None = None, italic: bool | None = None) -> None:
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def _configure_styles(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    normal.font.size = Pt(12)
    for name, size, bold in (("Heading 1", 12, True), ("Heading 2", 12, True), ("Heading 3", 12, True)):
        style = doc.styles[name]
        style.font.name = FONT
        style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        style.font.size = Pt(size)
        style.font.bold = bold
        style.font.all_caps = False


def _configure_section(section) -> None:
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(2.0)
    section.header_distance = Cm(0.8)
    section.footer_distance = Cm(0.7)

    footer = section.footer
    footer.is_linked_to_previous = False
    footer.paragraphs[0].clear()
    footer.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp = footer.paragraphs[0]
    fp.paragraph_format.space_before = Pt(0)
    fp.paragraph_format.space_after = Pt(0)
    fp.paragraph_format.line_spacing = 1.0
    for idx, line in enumerate(FOOTER_TEXT.split("\n")):
        if idx:
            fp.add_run().add_break()
        run = fp.add_run(line)
        _set_run_font(run, size=8)
    page = footer.add_paragraph()
    page.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    page.paragraph_format.space_before = Pt(0)
    page.paragraph_format.space_after = Pt(0)
    _add_page_number(page)
    for run in page.runs:
        _set_run_font(run, size=8)


def _new_paragraph(doc: Document, text: str, *, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                   first_line: float | None = 1.25, left: float | None = None,
                   before: float = 0, after: float = 6, line: float = 1.5,
                   bold: bool = False, italic: bool = False, size: float = 12):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if first_line is not None:
        pf.first_line_indent = Cm(first_line)
    if left is not None:
        pf.left_indent = Cm(left)
    run = p.add_run(text.strip())
    _set_run_font(run, size=size, bold=bold, italic=italic)
    return p


def _add_heading(doc: Document, text: str, level: int = 1):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if level == 1 else WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.first_line_indent = Cm(0)
    pf.left_indent = Cm(0)
    pf.space_before = Pt(12 if level == 1 else 8)
    pf.space_after = Pt(8)
    pf.line_spacing = 1.0
    r = p.add_run(text.strip())
    _set_run_font(r, size=12, bold=True)
    return p


def _add_signature_block(doc: Document, lines: list[str]) -> None:
    table = doc.add_table(rows=1, cols=min(3, max(1, len(lines))))
    table.autofit = True
    for cell, text in zip(table.rows[0].cells, lines):
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        _set_cell_borderless(cell)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        for idx, part in enumerate(text.split("\n")):
            if idx:
                p.add_run().add_break()
            r = p.add_run(part)
            _set_run_font(r, size=10, bold=idx == 1)


def _iter_blocks(conteudo: str) -> Iterable[str]:
    # Preserva quebras entre blocos, mas elimina excesso de linhas vazias.
    current: list[str] = []
    for raw in conteudo.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if line:
            current.append(line)
        elif current:
            yield " ".join(current)
            current = []
    if current:
        yield " ".join(current)


def _is_signature(block: str) -> bool:
    return "OAB/" in block.upper() or block.startswith("____")


def gerar_docx(conteudo: str, titulo: str | None = None) -> bytes:
    """Recebe o texto da peça e devolve DOCX com padrão Roesel Advogados."""
    doc = Document()
    _configure_styles(doc)
    _configure_section(doc.sections[0])

    blocks = list(_iter_blocks(conteudo))
    signature_candidates: list[str] = []
    for block in blocks:
        if _is_signature(block):
            signature_candidates.append(block)

    for idx, block in enumerate(blocks):
        upper = block.upper()
        if idx and upper.startswith("EGRÉGIO TRIBUNAL"):
            doc.add_page_break()
        if _ADDRESS.match(block):
            _new_paragraph(doc, block, align=WD_ALIGN_PARAGRAPH.CENTER, first_line=None,
                           before=0, after=12, line=1.0, bold=True)
        elif _PROCESS.match(block):
            _new_paragraph(doc, block, align=WD_ALIGN_PARAGRAPH.LEFT, first_line=None,
                           before=0, after=3, line=1.0)
        elif _ROMAN_HEADING.match(block) or _SUBHEADING.match(block):
            _add_heading(doc, block, level=2 if "." in block.split("–", 1)[0] else 1)
        elif upper in {"RAZÕES DE RECURSO ORDINÁRIO", "CONTESTAÇÃO", "RECURSO ORDINÁRIO"}:
            _add_heading(doc, block.upper(), level=1)
        elif _LIST.match(block):
            _new_paragraph(doc, block, align=WD_ALIGN_PARAGRAPH.LEFT, first_line=None,
                           left=1.0, before=0, after=3, line=1.15)
        elif _QUOTE.match(block) or (block.startswith("(") and len(block) > 80):
            _new_paragraph(doc, block, align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line=None,
                           left=1.25, before=3, after=6, line=1.15, italic=False)
        elif block.startswith("Nesses termos") or block.startswith("Nestes termos"):
            _new_paragraph(doc, block, align=WD_ALIGN_PARAGRAPH.LEFT, first_line=None,
                           before=12, after=12, line=1.0)
        elif "pede deferimento" in block.lower():
            _new_paragraph(doc, block, align=WD_ALIGN_PARAGRAPH.LEFT, first_line=None,
                           before=6, after=6, line=1.0)
        elif _is_signature(block):
            _new_paragraph(doc, block, align=WD_ALIGN_PARAGRAPH.CENTER, first_line=None,
                           before=3, after=3, line=1.0, size=10)
        else:
            _new_paragraph(doc, block, align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line=1.25,
                           before=0, after=6, line=1.5)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
