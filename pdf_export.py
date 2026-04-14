"""Génération de PDF mis en page aux couleurs Ramery."""

from __future__ import annotations

import re
import urllib.request
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

# ── Palette Ramery ─────────────────────────────────────────────────────────
BLUE  = (25,  60, 108)
RED   = (211,  36,  34)
WHITE = (255, 255, 255)
DARK  = ( 20,  30,  48)
MUTED = (100, 120, 150)
LIGHT = (235, 241, 250)

ASSETS_DIR = Path(__file__).parent / "assets"
FONTS_DIR  = ASSETS_DIR / "fonts"

LOGO_PATH = next(
    (ASSETS_DIR / f for f in ["logo.png", "logo.jpg", "logo.jpeg"]
     if (ASSETS_DIR / f).exists()),
    None,
)

# ── Téléchargement automatique des polices Unicode ─────────────────────────
_FONT_URLS = {
    "regular": (
        "DejaVuSans.ttf",
        "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37.3/ttf/DejaVuSans.ttf",
    ),
    "bold": (
        "DejaVuSans-Bold.ttf",
        "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37.3/ttf/DejaVuSans-Bold.ttf",
    ),
}

def _ensure_fonts() -> tuple[Path, Path]:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    paths = {}
    for key, (filename, url) in _FONT_URLS.items():
        dest = FONTS_DIR / filename
        if not dest.exists():
            print(f"[PDF] Téléchargement de la police {filename}…")
            urllib.request.urlretrieve(url, dest)
        paths[key] = dest
    return paths["regular"], paths["bold"]


# ── Nettoyage markdown inline ───────────────────────────────────────────────
def _strip_md_inline(text: str) -> str:
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"_{1,2}(.+?)_{1,2}", r"\1", text)
    # Seuls les caractères vraiment non imprimables sont remplacés
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text.strip()


# ── Classe PDF ──────────────────────────────────────────────────────────────
class RameryPDF(FPDF):

    def __init__(self, title: str = "Compte rendu"):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.title_text = title
        self.set_auto_page_break(auto=True, margin=22)
        self.set_margins(left=18, top=18, right=18)
        self._font_regular = ""
        self._font_bold    = ""

    def setup_fonts(self, regular: Path, bold: Path) -> None:
        self.add_font("DejaVu",  "",  str(regular))
        self.add_font("DejaVu",  "B", str(bold))
        self._font_regular = "DejaVu"
        self._font_bold    = "DejaVu"

    def _f(self, style: str = "", size: int = 9) -> None:
        self.set_font(self._font_regular if style == "" else self._font_bold,
                      style if style != "B" else "",
                      size)
        # fpdf2 avec add_font n'utilise pas le 2e arg pour B — on passe le bon nom
        self.set_font("DejaVu", style, size)

    def header(self):
        self.set_fill_color(*BLUE)
        self.rect(0, 0, 210, 11, "F")
        if LOGO_PATH:
            try:
                self.image(str(LOGO_PATH), x=4, y=1.2, h=8.5)
            except Exception:
                pass
        self.set_font("DejaVu", "B", 8)
        self.set_text_color(*WHITE)
        self.set_xy(0, 1.5)
        self.cell(205, 8, "Meet Notes  -  Ramery", align="R")
        self.set_xy(18, 18)

    def footer(self):
        self.set_y(-12)
        self.set_draw_color(*RED)
        self.set_line_width(0.4)
        self.line(18, self.get_y(), 192, self.get_y())
        self.ln(1.5)
        self.set_font("DejaVu", "", 7)
        self.set_text_color(*MUTED)
        date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
        self.cell(0, 5, f"Généré le {date_str}  ·  Page {self.page_no()}", align="C")


# ── Renderer markdown ───────────────────────────────────────────────────────
def _render_markdown(pdf: RameryPDF, markdown: str) -> None:
    W = 174
    in_table  = False
    row_index = 0

    for raw in markdown.splitlines():
        line = raw.strip()

        try:
            pdf.set_x(18)

            # H1
            if line.startswith("# ") and not line.startswith("## "):
                pdf.ln(3)
                pdf.set_font("DejaVu", "B", 14)
                pdf.set_text_color(*BLUE)
                pdf.multi_cell(W, 8, _strip_md_inline(line[2:]))
                pdf.set_fill_color(*RED)
                pdf.rect(18, pdf.get_y(), W, 0.7, "F")
                pdf.ln(4)

            # H2
            elif line.startswith("## "):
                in_table  = False
                row_index = 0
                pdf.ln(3)
                # Assez de place pour le bloc H2 ? (hauteur ~9mm)
                if pdf.get_y() > 260:
                    pdf.add_page()
                y = pdf.get_y()
                pdf.set_fill_color(*BLUE)
                pdf.rect(18, y, 2, 8, "F")
                pdf.set_fill_color(*LIGHT)
                pdf.rect(20, y, 172, 8, "F")
                pdf.set_font("DejaVu", "B", 10)
                pdf.set_text_color(*BLUE)
                pdf.set_xy(22, y + 1.5)
                pdf.cell(168, 6, _strip_md_inline(line[3:]))
                pdf.set_xy(18, y + 9)
                pdf.ln(1)

            # H3
            elif line.startswith("### "):
                pdf.ln(2)
                pdf.set_font("DejaVu", "B", 9)
                pdf.set_text_color(*DARK)
                pdf.multi_cell(W, 6, _strip_md_inline(line[4:]))
                pdf.ln(1)

            # Tableau
            elif line.startswith("|") and line.endswith("|"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if all(set(c.replace(":", "").replace("-", "")) == set() for c in cells):
                    row_index = 1
                    continue
                n_cols = max(len(cells), 1)
                col_w  = max(W / n_cols, 15)
                in_table = True

                if row_index == 0:
                    pdf.set_fill_color(*BLUE)
                    pdf.set_text_color(*WHITE)
                    pdf.set_font("DejaVu", "B", 7.5)
                    for cell in cells:
                        pdf.cell(col_w, 6, _strip_md_inline(cell)[:38], border=0, fill=True)
                    pdf.ln(6)
                else:
                    pdf.set_fill_color(*(LIGHT if row_index % 2 == 0 else WHITE))
                    pdf.set_text_color(*DARK)
                    pdf.set_font("DejaVu", "", 7.5)
                    for cell in cells:
                        pdf.cell(col_w, 5.5, _strip_md_inline(cell)[:48], border=0, fill=True)
                    pdf.ln(5.5)
                row_index += 1

            # Puce
            elif line.startswith(("- ", "* ", "+ ")):
                in_table = False
                pdf.set_font("DejaVu", "", 9)
                pdf.set_text_color(*DARK)
                pdf.set_fill_color(*RED)
                pdf.ellipse(19, pdf.get_y() + 2, 1.5, 1.5, "F")
                pdf.set_x(22)
                pdf.multi_cell(170, 5.5, _strip_md_inline(line[2:]))

            # Puce indentée
            elif line.startswith(("  - ", "  * ")):
                pdf.set_font("DejaVu", "", 8.5)
                pdf.set_text_color(*MUTED)
                pdf.set_x(26)
                pdf.multi_cell(164, 5, "- " + _strip_md_inline(line[4:]))

            # Ligne vide
            elif line == "":
                in_table  = False
                row_index = 0
                pdf.ln(2)

            # Séparateur
            elif line.startswith("---"):
                pdf.ln(2)
                pdf.set_draw_color(*LIGHT)
                pdf.set_line_width(0.3)
                pdf.line(18, pdf.get_y(), 192, pdf.get_y())
                pdf.ln(3)

            # Texte normal
            else:
                in_table = False
                pdf.set_font("DejaVu", "", 9)
                pdf.set_text_color(*DARK)
                pdf.multi_cell(W, 5.5, _strip_md_inline(line))

        except Exception as e:
            print(f"[PDF] Ligne ignorée : {line[:60]} — {e}")
            pdf.set_x(18)
            continue


# ── Point d'entrée ──────────────────────────────────────────────────────────
def generate_pdf(report_md: str, audio_stem: str) -> bytes:
    regular, bold = _ensure_fonts()

    pdf = RameryPDF(title=audio_stem)
    pdf.setup_fonts(regular, bold)
    pdf.add_page()

    # Titre
    pdf.ln(6)
    pdf.set_font("DejaVu", "B", 18)
    pdf.set_text_color(*BLUE)
    pdf.multi_cell(174, 10, audio_stem.replace("_", " "), align="C")
    pdf.ln(2)
    pdf.set_fill_color(*RED)
    pdf.rect(60, pdf.get_y(), 90, 0.8, "F")
    pdf.ln(5)
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(*MUTED)
    date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    pdf.cell(0, 6, f"Compte rendu généré le {date_str}", align="C")
    pdf.ln(10)

    _render_markdown(pdf, report_md)

    return bytes(pdf.output())
