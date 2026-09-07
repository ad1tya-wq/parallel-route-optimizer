#!/usr/bin/env python3
"""
Build the Review-2 report (.docx).

Numbers and tables are read from results/analysis/*.csv at build time, so the
document cannot drift away from the measurements. Prose lives in this file.

    python report/build_report.py
"""
import csv
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / "results" / "analysis"
FIGURES = ROOT / "results" / "figures"
OUT = ROOT / "report" / "ParallelRoute_Review2_Report.docx"

NAVY = RGBColor(0x0B, 0x3D, 0x5C)
TEAL = RGBColor(0x1C, 0x72, 0x93)
SLATE = RGBColor(0x51, 0x69, 0x7A)
INK = RGBColor(0x1A, 0x1A, 0x1A)


def read(name):
    p = ANALYSIS / name
    if not p.exists():
        return []
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def shade(cell, hexcolor):
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:fill"), hexcolor)
    cell._tc.get_or_add_tcPr().append(el)


class Report:
    def __init__(self):
        d = Document()
        for s in d.sections:
            s.top_margin = s.bottom_margin = Inches(0.9)
            s.left_margin = s.right_margin = Inches(1.0)
        st = d.styles["Normal"]
        st.font.name = "Calibri"
        st.font.size = Pt(10.5)
        st.font.color.rgb = INK
        st.paragraph_format.space_after = Pt(7)
        st.paragraph_format.line_spacing = 1.14
        self.d = d

    # --- block helpers ---
    def title(self, text, sub=None, meta=None):
        p = self.d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(text)
        r.font.name = "Cambria"; r.font.size = Pt(19); r.font.bold = True
        r.font.color.rgb = NAVY
        if sub:
            p = self.d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(sub)
            r.font.name = "Cambria"; r.font.size = Pt(12); r.font.color.rgb = TEAL
        if meta:
            p = self.d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(meta)
            r.font.size = Pt(9.5); r.font.color.rgb = SLATE
        self.d.add_paragraph()

    def h1(self, text):
        p = self.d.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(5)
        r = p.add_run(text)
        r.font.name = "Cambria"; r.font.size = Pt(13.5); r.font.bold = True
        r.font.color.rgb = NAVY

    def h2(self, text):
        p = self.d.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(text)
        r.font.name = "Cambria"; r.font.size = Pt(11.5); r.font.bold = True
        r.font.color.rgb = TEAL

    def p(self, text, italic=False, size=10.5):
        par = self.d.add_paragraph()
        r = par.add_run(text)
        r.font.size = Pt(size); r.italic = italic
        if italic:
            r.font.color.rgb = SLATE
        return par

    def rich(self, parts):
        """parts: list of (text, bold) tuples."""
        par = self.d.add_paragraph()
        for t, b in parts:
            r = par.add_run(t)
            r.font.size = Pt(10.5); r.bold = b
        return par

    def bullet(self, text, bold_head=None):
        par = self.d.add_paragraph(style="List Bullet")
        par.paragraph_format.space_after = Pt(3)
        if bold_head:
            r = par.add_run(bold_head + " ")
            r.font.size = Pt(10.5); r.bold = True
        r = par.add_run(text); r.font.size = Pt(10.5)
        return par

    def table(self, headers, rows, widths=None, caption=None, note=None):
        t = self.d.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, h in enumerate(headers):
            c = t.rows[0].cells[i]
            c.text = ""
            r = c.paragraphs[0].add_run(str(h))
            r.font.bold = True; r.font.size = Pt(9); r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            shade(c, "0B3D5C")
        for ri, row in enumerate(rows):
            cells = t.add_row().cells
            for i, v in enumerate(row):
                cells[i].text = ""
                par = cells[i].paragraphs[0]
                if i > 0:
                    par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                r = par.add_run(str(v))
                r.font.size = Pt(9)
                if str(v).startswith("**"):
                    r.text = str(v).strip("*"); r.font.bold = True
            if ri % 2 == 1:
                for c in cells:
                    shade(c, "F2F6F8")
        if widths:
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Inches(w)
        if caption:
            par = self.d.add_paragraph()
            par.paragraph_format.space_before = Pt(3)
            r = par.add_run(caption)
            r.font.size = Pt(8.5); r.italic = True; r.font.color.rgb = SLATE
        if note:
            par = self.d.add_paragraph()
            r = par.add_run(note)
            r.font.size = Pt(8.5); r.font.color.rgb = SLATE
        return t

    def figure(self, name, caption, width=6.2):
        p = FIGURES / name
        if not p.exists():
            return
        self.d.add_picture(str(p), width=Inches(width))
        self.d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        par = self.d.add_paragraph(); par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = par.add_run(caption)
        r.font.size = Pt(8.5); r.italic = True; r.font.color.rgb = SLATE

    def pagebreak(self):
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def save(self):
        self.d.save(OUT)
        print(f"wrote {OUT.relative_to(ROOT)}")
