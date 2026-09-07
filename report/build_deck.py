#!/usr/bin/env python3
"""
Build the Review-2 slide deck (.pptx).

Continues the visual language of the Review-1 deck -- Cambria headings, Calibri
body, navy/teal/amber palette on a light ground, dark title slide -- so the two
presentations read as one series. Content numbers are pulled from
results/analysis/*.csv where possible, so the deck cannot drift away from the
measurements.

    python report/build_deck.py
"""
import csv
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / "results" / "analysis"
FIGURES = ROOT / "results" / "figures"
OUT = ROOT / "report" / "ParallelRoute_Review2_Deck.pptx"

# --- palette (taken from the Review-1 deck) --------------------------------
NAVY = RGBColor(0x0B, 0x3D, 0x5C)
TEAL = RGBColor(0x1C, 0x72, 0x93)
AMBER = RGBColor(0xF2, 0xA5, 0x41)
SLATE = RGBColor(0x51, 0x69, 0x7A)
MIST = RGBColor(0xCF, 0xE0, 0xE9)
HAZE = RGBColor(0xAF, 0xC3, 0xD0)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PAPER = RGBColor(0xF7, 0xF9, 0xFA)
RED = RGBColor(0xC0, 0x39, 0x2B)
GREEN = RGBColor(0x1E, 0x7A, 0x5A)

W, H = Inches(13.333), Inches(7.5)
M = Inches(0.72)          # page margin
HEAD = "Cambria"
BODY = "Calibri"


def read_csv(name):
    p = ANALYSIS / name
    if not p.exists():
        return []
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


# --- primitives ------------------------------------------------------------
def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def bg(slide, color):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color


def rect(slide, x, y, w, h, fill=None, line=None, lw=Pt(1)):
    from pptx.enum.shapes import MSO_SHAPE
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    s.adjustments[0] = 0.045
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = lw
    s.shadow.inherit = False
    return s


def text(slide, x, y, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         line_spacing=1.0, space_after=0):
    """runs: list of (text, font, size_pt, color, bold) or a list of such lists
    (one inner list per paragraph)."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    paras = runs if runs and isinstance(runs[0], list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        p.space_after = Pt(space_after)
        for t, fname, size, color, bold in para:
            r = p.add_run()
            r.text = t
            r.font.name = fname
            r.font.size = Pt(size)
            r.font.color.rgb = color
            r.font.bold = bold
    return tb


def eyebrow(slide, label, color=TEAL):
    text(slide, M, Inches(0.46), Inches(8), Inches(0.28),
         [(label.upper(), BODY, 12.5, color, True)])


def title(slide, s, sub=None, color=NAVY):
    text(slide, M, Inches(0.78), W - 2 * M, Inches(0.72),
         [(s, HEAD, 29, color, True)])
    if sub:
        text(slide, M, Inches(1.52), W - 2 * M, Inches(0.4),
             [(sub, BODY, 13.5, SLATE, False)])


def footer(slide, n):
    text(slide, W - M - Inches(0.6), H - Inches(0.5), Inches(0.6), Inches(0.25),
         [(str(n), BODY, 10, HAZE, False)], align=PP_ALIGN.RIGHT)


def stat(slide, x, y, w, value, label, vcolor=TEAL, note=None):
    rect(slide, x, y, w, Inches(1.42), fill=WHITE, line=MIST)
    text(slide, x + Inches(0.22), y + Inches(0.17), w - Inches(0.44), Inches(0.5),
         [(value, HEAD, 25, vcolor, True)])
    text(slide, x + Inches(0.22), y + Inches(0.72), w - Inches(0.44), Inches(0.6),
         [(label, BODY, 11, SLATE, False)], line_spacing=1.12)
    if note:
        text(slide, x + Inches(0.22), y + Inches(1.12), w - Inches(0.44), Inches(0.26),
             [(note, BODY, 9, HAZE, False)])


def bullets(slide, x, y, w, items, size=12.5, gap=0.5, marker=True):
    yy = y
    for it in items:
        if isinstance(it, tuple):
            head, rest = it
        else:
            head, rest = None, it
        if marker:
            rect(slide, x, yy + Inches(0.07), Inches(0.055), Inches(0.19), fill=AMBER)
        runs = []
        if head:
            runs.append((head + "  ", BODY, size, NAVY, True))
        runs.append((rest, BODY, size, SLATE, False))
        tb = text(slide, x + Inches(0.2), yy, w - Inches(0.2), Inches(gap), runs,
                  line_spacing=1.22)
        yy += Inches(gap)
    return yy


def picture(slide, path, x, y, w=None, h=None):
    if not Path(path).exists():
        return None
    return slide.shapes.add_picture(str(path), x, y, width=w, height=h)


def table(slide, x, y, w, rows, col_w=None, size=11, header_bg=NAVY, row_h=0.34):
    """rows[0] is the header. Returns bottom y."""
    ncol = len(rows[0])
    col_w = col_w or [w / ncol] * ncol
    yy = y
    for ri, row in enumerate(rows):
        xx = x
        if ri == 0:
            rect(slide, x, yy, w, Inches(row_h), fill=header_bg)
        elif ri % 2 == 0:
            rect(slide, x, yy, w, Inches(row_h), fill=PAPER)
        for ci, cell in enumerate(row):
            val, col, bold = (cell if isinstance(cell, tuple)
                              else (cell, WHITE if ri == 0 else SLATE, ri == 0))
            text(slide, xx + Inches(0.1), yy + Inches(0.06), col_w[ci] - Inches(0.12),
                 Inches(row_h), [(str(val), BODY, size, col, bold)],
                 align=PP_ALIGN.LEFT if ci == 0 else PP_ALIGN.RIGHT)
            xx += col_w[ci]
        yy += Inches(row_h)
    return yy


def callout(slide, x, y, w, h, head, body, accent=AMBER):
    rect(slide, x, y, w, h, fill=WHITE, line=MIST)
    rect(slide, x, y, Inches(0.055), h, fill=accent)
    text(slide, x + Inches(0.24), y + Inches(0.16), w - Inches(0.46), Inches(0.3),
         [(head, BODY, 11.5, NAVY, True)])
    text(slide, x + Inches(0.24), y + Inches(0.5), w - Inches(0.46), h - Inches(0.62),
         [(body, BODY, 11, SLATE, False)], line_spacing=1.2)
