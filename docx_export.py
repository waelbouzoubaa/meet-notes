"""Génération de rapports Word (.docx) aux couleurs Ramery."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# ── Palette Ramery ─────────────────────────────────────────────────────────────
BLUE  = RGBColor(25,  60, 108)
RED   = RGBColor(211, 36,  34)
DARK  = RGBColor(20,  30,  48)
MUTED = RGBColor(100, 120, 150)


def _strip_md_inline(text: str) -> str:
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"_{1,2}(.+?)_{1,2}", r"\1", text)
    return text.strip()


def _add_horizontal_rule(doc: Document) -> None:
    """Ajoute une ligne horizontale rouge Ramery."""
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "D32422")
    pBdr.append(bottom)
    pPr.append(pBdr)
    p.paragraph_format.space_after = Pt(4)


def generate_docx(report_md: str, title: str) -> bytes:
    """Convertit un rapport Markdown en .docx aux couleurs Ramery.

    Parameters
    ----------
    report_md : rapport au format Markdown
    title     : titre du document (nom de la réunion)

    Returns
    -------
    Contenu du fichier .docx en bytes
    """
    doc = Document()

    # ── Marges ─────────────────────────────────────────────────────────────────
    for section in doc.sections:
        section.top_margin    = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin   = Cm(2.5)
        section.right_margin  = Cm(2.5)

    # ── Titre principal ────────────────────────────────────────────────────────
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p_title.add_run(title.replace("_", " "))
    run.bold      = True
    run.font.size = Pt(20)
    run.font.color.rgb = BLUE

    _add_horizontal_rule(doc)

    # Sous-titre date
    date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    p_date = doc.add_paragraph(f"Compte rendu généré le {date_str}")
    p_date.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_date.runs[0].font.color.rgb = MUTED
    p_date.runs[0].font.size = Pt(9)
    doc.add_paragraph()

    # ── Rendu Markdown ─────────────────────────────────────────────────────────
    for raw in report_md.splitlines():
        line = raw.strip()

        # H1
        if line.startswith("# ") and not line.startswith("## "):
            p = doc.add_heading(_strip_md_inline(line[2:]), level=1)
            p.runs[0].font.color.rgb = BLUE
            p.runs[0].font.size = Pt(14)

        # H2
        elif line.startswith("## "):
            p = doc.add_heading(_strip_md_inline(line[3:]), level=2)
            p.runs[0].font.color.rgb = BLUE
            p.runs[0].font.size = Pt(12)

        # H3
        elif line.startswith("### "):
            p = doc.add_heading(_strip_md_inline(line[4:]), level=3)
            p.runs[0].font.color.rgb = DARK
            p.runs[0].font.size = Pt(10)

        # Puce
        elif line.startswith(("- ", "* ", "+ ")):
            p = doc.add_paragraph(_strip_md_inline(line[2:]), style="List Bullet")
            p.runs[0].font.size = Pt(10)

        # Puce indentée
        elif line.startswith(("  - ", "  * ")):
            p = doc.add_paragraph(_strip_md_inline(line[4:]), style="List Bullet 2")
            p.runs[0].font.size = Pt(9)

        # Tableau — ligne d'en-tête ou données
        elif line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            # Ligne de séparateur (---)
            if all(set(c.replace(":", "").replace("-", "")) == set() for c in cells):
                continue
            # Première vraie ligne de tableau → créer la table
            # (on crée une table d'une ligne à la fois)
            tbl = doc.add_table(rows=1, cols=len(cells))
            tbl.style = "Table Grid"
            row = tbl.rows[0]
            for i, cell_text in enumerate(cells):
                cell = row.cells[i]
                cell.text = _strip_md_inline(cell_text)
                cell.paragraphs[0].runs[0].font.size = Pt(9)

        # Séparateur
        elif line.startswith("---"):
            _add_horizontal_rule(doc)

        # Ligne vide
        elif line == "":
            doc.add_paragraph()

        # Texte normal
        else:
            p = doc.add_paragraph(_strip_md_inline(line))
            p.runs[0].font.size = Pt(10) if p.runs else None

    # ── Export en bytes ────────────────────────────────────────────────────────
    import io
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
