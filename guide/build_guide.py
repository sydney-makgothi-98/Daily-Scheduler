"""Builds guide/DjangoForDummies.pdf from guide/chapters/*.txt.

Run:  uv run python guide/build_guide.py

Chapter markup (plain text, one idea per line):
  # Title            part divider (own page)
  ## Title           chapter (new page, in TOC + bookmarks)
  ### Title          section        #### Title   sub-section
  ```py ... ```      code block (language tag is shown as a label)
  !why: text         green "Why it is written this way" box   (block continues until a blank line)
  !without: text     red   "What would happen otherwise" box
  !alt: text         blue  "Alternative / simpler way" box
  !tip: text         grey  tip box
  [[diagram:name]]   a diagram from diagrams.py
  | a | b |          table (first row = header)
  - item / 1. item   lists
  **bold**  `code`   inline styles
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

sys.path.insert(0, str(Path(__file__).parent))
import diagrams  # noqa: E402

HERE = Path(__file__).parent
FONTS = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Body", str(FONTS / "arial.ttf")))
pdfmetrics.registerFont(TTFont("Body-Bold", str(FONTS / "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("Body-Italic", str(FONTS / "ariali.ttf")))
pdfmetrics.registerFont(TTFont("Body-BoldItalic", str(FONTS / "arialbi.ttf")))
pdfmetrics.registerFont(TTFont("Mono", str(FONTS / "consola.ttf")))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic", boldItalic="Body-BoldItalic")

INK = colors.HexColor("#1e293b")
ACCENT = colors.HexColor("#6d28d9")
BOX = {
    "why": ("WHY IT IS WRITTEN THIS WAY", colors.HexColor("#ecfdf5"), colors.HexColor("#059669")),
    "without": ("WHAT HAPPENS WITHOUT IT", colors.HexColor("#fef2f2"), colors.HexColor("#dc2626")),
    "alt": ("ALTERNATIVE / SIMPLER WAY", colors.HexColor("#eff6ff"), colors.HexColor("#2563eb")),
    "tip": ("TIP", colors.HexColor("#f1f5f9"), colors.HexColor("#64748b")),
}

S = {
    "body": ParagraphStyle("body", fontName="Body", fontSize=9.6, leading=13.6, textColor=INK, alignment=TA_LEFT, spaceAfter=5),
    "h1": ParagraphStyle("h1", fontName="Body-Bold", fontSize=30, leading=36, textColor=ACCENT, spaceAfter=14),
    "h2": ParagraphStyle("h2", fontName="Body-Bold", fontSize=21, leading=26, textColor=ACCENT, spaceAfter=10),
    "h3": ParagraphStyle("h3", fontName="Body-Bold", fontSize=13.5, leading=17, textColor=INK, spaceBefore=10, spaceAfter=5),
    "h4": ParagraphStyle("h4", fontName="Body-Bold", fontSize=11, leading=14, textColor=ACCENT, spaceBefore=7, spaceAfter=3),
    "code": ParagraphStyle("code", fontName="Mono", fontSize=7.8, leading=9.8, textColor=colors.HexColor("#0f172a")),
    "boxtitle": ParagraphStyle("boxtitle", fontName="Body-Bold", fontSize=7.5, leading=9, spaceAfter=2),
    "box": ParagraphStyle("box", fontName="Body", fontSize=9.2, leading=12.8, textColor=INK),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=8.6, leading=11.2, textColor=INK),
    "cellh": ParagraphStyle("cellh", fontName="Body-Bold", fontSize=8.6, leading=11.2, textColor=colors.white),
    "toc1": ParagraphStyle("toc1", fontName="Body-Bold", fontSize=11, leading=15, spaceBefore=6),
    "toc2": ParagraphStyle("toc2", fontName="Body", fontSize=9.5, leading=12, leftIndent=14),
}

FRAME_W = A4[0] - 36 * mm


def clean(text: str) -> str:
    """Escape for reportlab and drop glyphs the fonts lack (emoji)."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = "".join(c for c in text if ord(c) < 0x2E80 or c in "\u2192\u2190")
    text = re.sub(r"[\ufe0f\u200d]", "", text)
    return text


def inline(text: str) -> str:
    text = clean(text)
    text = re.sub(r"`([^`]+)`", r'<font name="Mono" size="8.6" color="#9d174d">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text


def wrap_code(code: str, width: int = 100) -> str:
    out = []
    for line in code.expandtabs(4).split("\n"):
        line = "".join(c for c in line if ord(c) < 0x2E80)
        while len(line) > width:
            out.append(line[:width] + " \\")
            line = "      " + line[width:]
        out.append(line)
    return "\n".join(out)


class Doc(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
            title="Django for Dummies - taught through the Daily Schedule App", author="Daily Schedule project",
        )
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=self._footer)])
        self._n = 0

    def _footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Body", 8)
        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.drawString(18 * mm, 10 * mm, "Django for Dummies - Daily Schedule App")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(doc.page))
        canvas.restoreState()

    def afterFlowable(self, flowable):
        level = getattr(flowable, "_toc_level", None)
        if level is None:
            return
        text = flowable.getPlainText()
        key = "h%d-%s" % (level, hashlib.md5(text.encode("utf-8")).hexdigest()[:10])
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(text, key, level=level, closed=level > 0)
        self.notify("TOCEntry", (level, text, self.page, key))


def heading(text: str, style: str, level: int | None) -> Paragraph:
    p = Paragraph(inline(text), S[style])
    if level is not None:
        p._toc_level = level
    return p


def box(kind: str, lines: list[str]) -> Table:
    title, bg, edge = BOX[kind]
    body = " ".join(l.strip() for l in lines)
    cell = [Paragraph(f'<font color="{edge.hexval().replace("0x", "#")}">{title}</font>', S["boxtitle"]), Paragraph(inline(body), S["box"])]
    t = Table([[cell]], colWidths=[FRAME_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, edge),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def code_block(lang: str, code: str) -> Table:
    pre = Preformatted(wrap_code(code.rstrip("\n")), S["code"])
    label = Paragraph(f'<font color="#64748b">{clean(lang or "text")}</font>', S["boxtitle"])
    t = Table([[label], [pre]], colWidths=[FRAME_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    t.splitByRow = 1
    t.repeatRows = 1
    # Short blocks stay on one page so the label is never stranded from its code.
    return KeepTogether([t]) if code.count(chr(10)) < 38 else t


def table_block(rows: list[list[str]]) -> Table:
    ncols = max(len(r) for r in rows)
    data = []
    for i, r in enumerate(rows):
        r = r + [""] * (ncols - len(r))
        data.append([Paragraph(inline(c), S["cellh" if i == 0 else "cell"]) for c in r])
    t = Table(data, colWidths=[FRAME_W / ncols] * ncols, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def parse(text: str) -> list:
    flow: list = []
    lines = text.split("\n")
    i = 0
    para: list[str] = []

    def flush():
        nonlocal para
        if para:
            flow.append(Paragraph(inline(" ".join(para)), S["body"]))
            para = []

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith("```"):
            flush()
            lang, buf = s[3:].strip(), []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            flow.append(code_block(lang, "\n".join(buf)))
            flow.append(Spacer(1, 5))
        elif s.startswith("#### "):
            flush(); flow.append(heading(s[5:], "h4", None))
        elif s.startswith("### "):
            flush(); flow.append(heading(s[4:], "h3", 1))
        elif s.startswith("## "):
            flush(); flow.append(PageBreak()); flow.append(heading(s[3:], "h2", 0)); flow.append(Spacer(1, 4))
        elif s.startswith("# "):
            flush(); flow.append(PageBreak()); flow.append(Spacer(1, 90 * mm)); flow.append(heading(s[2:], "h1", None))
        elif s.startswith("[[diagram:"):
            flush()
            name = s[len("[[diagram:"):-2]
            flow.append(diagrams.get(name, FRAME_W))
            flow.append(Spacer(1, 6))
        elif re.match(r"^!(why|without|alt|tip):", s):
            flush()
            kind = s[1:s.index(":")]
            buf = [s[s.index(":") + 1:]]
            while i + 1 < len(lines) and lines[i + 1].strip():
                i += 1
                buf.append(lines[i])
            flow.append(box(kind, buf))
            flow.append(Spacer(1, 6))
        elif s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"-+", c) for c in cells):
                    rows.append(cells)
                i += 1
            i -= 1
            flow.append(table_block(rows))
            flow.append(Spacer(1, 6))
        elif re.match(r"^(- |\d+\. )", s):
            flush()
            ordered = bool(re.match(r"^\d+\. ", s))
            items = []
            while i < len(lines) and re.match(r"^(- |\d+\. )", lines[i].strip()):
                items.append(re.sub(r"^(- |\d+\. )", "", lines[i].strip()))
                i += 1
            i -= 1
            flow.append(ListFlowable(
                [ListItem(Paragraph(inline(t), S["body"]), leftIndent=14) for t in items],
                bulletType="1" if ordered else "bullet", start=1 if ordered else "\u2022", leftIndent=14, bulletFontSize=8,
            ))
        elif not s:
            flush()
        else:
            para.append(s)
        i += 1
    flush()
    return flow


def main() -> None:
    out = HERE / "DjangoForDummies.pdf"
    story: list = [Spacer(1, 55 * mm), Paragraph("Django for Dummies", S["h1"]),
                   Paragraph("Learn Django by taking apart a real app: the Daily Schedule planner", S["h3"]),
                   Spacer(1, 6 * mm),
                   Paragraph("Theory first, with diagrams and worked examples. Then every file in the project, line by line: "
                             "why it is written that way, what would happen otherwise, and simpler or alternative ways "
                             "(such as class-based views).", S["body"]),
                   PageBreak(), Paragraph("Contents", S["h2"])]
    toc = TableOfContents()
    toc.levelStyles = [S["toc1"], S["toc2"]]
    story += [toc]
    for chapter in sorted((HERE / "chapters").glob("*.txt")):
        story += parse(chapter.read_text(encoding="utf-8"))
    doc = Doc(str(out))
    doc.multiBuild(story)
    print("wrote", out)


if __name__ == "__main__":
    main()
