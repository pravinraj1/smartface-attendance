"""Lightweight PDF report generation for attendance reports.

Uses ReportLab (pure Python, no system deps) so it runs fine on the
headless 512 MB Render instance. All fonts are the built-in Helvetica
(AFMs), so no font file is needed and CJK is not required.
"""
import io
from typing import List, Sequence, Optional
import datetime as _dt

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)

_HEADER_BG = colors.HexColor("#2b6cb0")
_ALT_BG = colors.HexColor("#f7fafc")
_HEADER_FG = colors.white


def _styles(result_title: str):
    ss = getSampleStyleSheet()
    title = ParagraphStyle(
        "RptTitle", parent=ss["Title"], fontSize=16, spaceAfter=4,
        textColor=colors.HexColor("#1a202c"),
    )
    subtitle = ParagraphStyle(
        "RptSub", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor("#718096"),
        spaceAfter=10, alignment=0,
    )
    return title, subtitle


def _numeric(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _text(value) -> str:
    if value is None:
        return "-"
    return str(value)


def build_table_pdf(
    title: str,
    subtitle: Optional[str],
    columns: Sequence[str],
    rows: Sequence[Sequence],
    *,
    landscape_page: bool = False,
    col_widths: Optional[List] = None,
    summary_block: Optional[List[tuple]] = None,
) -> bytes:
    """Render a titled table to a PDF and return the bytes."""
    page = landscape(A4) if landscape_page else A4
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=page,
        leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
        title=title,
    )

    title_style, subtitle_style = _styles(title)
    story = [Paragraph(title, title_style)]
    if subtitle:
        story.append(Paragraph(subtitle, subtitle_style))
    story.append(Spacer(1, 4 * mm))

    # Optional summary key/value block rendered as a small table.
    if summary_block:
        sum_rows = [[Paragraph(k, ParagraphStyle("k", parent=subtitle_style, fontSize=8.5, textColor=colors.HexColor("#2b6cb0"))),
                     Paragraph(v, ParagraphStyle("v", parent=subtitle_style, fontSize=8.5))] for k, v in summary_block]
        sum_tbl = Table(sum_rows, colWidths=[50 * mm, 80 * mm])
        sum_tbl.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#edf2f7")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(sum_tbl)
        story.append(Spacer(1, 4 * mm))

    header_row = list(columns)
    body = [[Paragraph(_text(c), ParagraphStyle(
                f"h{i}", parent=getSampleStyleSheet()["Normal"], fontSize=8,
                textColor=_HEADER_FG, alignment=0 if c != "Total Hours" else 1))
             for i, c in enumerate(header_row)]]
    for r in rows:
        body_row = []
        for i, val in enumerate(r):
            body_row.append(Paragraph(_text(val), ParagraphStyle(
                f"c{i}_{len(body)}", parent=getSampleStyleSheet()["Normal"], fontSize=8,
                textColor=colors.HexColor("#2d3748"))))
        body.append(body_row)

    widths = col_widths or None
    table = Table(body, colWidths=widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for ri in range(1, len(body)):
        if ri % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, ri), (-1, ri), _ALT_BG))
    table.setStyle(TableStyle(style_cmds))
    story.append(table)

    doc.build(story)
    return buf.getvalue()


def minutes_to_hours(total_minutes) -> str:
    m = _numeric(total_minutes)
    h = int(m // 60)
    rem = int(m % 60)
    return f"{h}h {rem}m"
