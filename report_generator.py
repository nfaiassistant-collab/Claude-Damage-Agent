"""
PDF report generator.
Builds a professional damage report PDF using ReportLab,
embedding company logo, damage findings table, and inspected photos.
"""

from datetime import datetime
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)

from config import COMPANY_LOGO_PATH
from damage_analyzer import DamageReport, PhotoFinding
from report_parser import ReportTemplate

# ── Brand colors ──────────────────────────────────────────────────────────────
DARK_BLUE = colors.HexColor("#1B3A6B")
LIGHT_BLUE = colors.HexColor("#4A90D9")
LIGHT_GRAY = colors.HexColor("#F5F5F5")
MID_GRAY = colors.HexColor("#CCCCCC")
RED = colors.HexColor("#CC2222")
ORANGE = colors.HexColor("#E07B00")
GREEN = colors.HexColor("#2A7A2A")
WHITE = colors.white
BLACK = colors.black

SEVERITY_COLOR = {
    "Severe": RED,
    "Moderate": ORANGE,
    "Minor": ORANGE,
    "No Damage Visible": GREEN,
    "Unknown": MID_GRAY,
    "Unable to assess": MID_GRAY,
}

PAGE_W, PAGE_H = LETTER
MARGIN = 0.75 * inch


def generate_report(
    damage_report: DamageReport,
    template: ReportTemplate,
    project_info: dict,
    output_path: Path,
    property_address: str = "",
    claim_number: str = "",
    inspector_name: str = "",
    homeowner_name: str = "",
    photo_selection_path: Path = None,
) -> Path:
    """
    Generate a PDF damage report and save to output_path.
    Returns the path to the saved PDF.
    """
    import json as _json

    # Apply photo selection/ordering if a selection file exists
    if photo_selection_path and photo_selection_path.exists():
        sel = _json.loads(photo_selection_path.read_text())
        ordered_nums = sel.get("ordered_photo_numbers", [])
        findings_by_num = {f.photo_number: f for f in damage_report.findings}
        damage_report.findings = [
            findings_by_num[n] for n in ordered_nums if n in findings_by_num
        ]
        print(f"  Photo selection applied: {len(damage_report.findings)} photos")

    styles = _build_styles()

    doc = BaseDocTemplate(
        str(output_path),
        pagesize=LETTER,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    frame = Frame(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN, id="main")
    doc.addPageTemplates([PageTemplate(id="main", frames=frame, onPage=_draw_footer)])

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story += _build_header(styles, project_info, property_address, claim_number, inspector_name, homeowner_name)
    story.append(Spacer(1, 0.2 * inch))

    # ── Executive Summary ─────────────────────────────────────────────────────
    story += _build_summary(styles, damage_report)
    story.append(Spacer(1, 0.3 * inch))

    # ── Photo Evidence ────────────────────────────────────────────────────────
    story += _build_photo_section(styles, damage_report)

    doc.build(story)
    print(f"\nReport saved: {output_path}")
    return output_path


# ── Section builders ──────────────────────────────────────────────────────────

def _build_header(styles, project_info, address, claim_number, inspector_name, homeowner_name=""):
    elements = []
    content_width = PAGE_W - 2 * MARGIN

    # Logo + title side by side
    logo_cell = ""
    if COMPANY_LOGO_PATH and Path(COMPANY_LOGO_PATH).exists():
        try:
            logo_img = _fit_image(COMPANY_LOGO_PATH, max_w=2.2 * inch, max_h=1.0 * inch)
            logo_cell = logo_img
        except Exception:
            logo_cell = Paragraph("BEARD ROOFING", styles["CompanyName"])
    else:
        logo_cell = Paragraph("BEARD ROOFING", styles["CompanyName"])

    title_cell = [
        Paragraph("ROOF DAMAGE REPORT", styles["ReportTitle"]),
        Paragraph(f"Inspection Date: {datetime.now().strftime('%B %d, %Y')}", styles["SubTitle"]),
    ]

    header_table = Table(
        [[logo_cell, title_cell]],
        colWidths=[2.5 * inch, content_width - 2.5 * inch],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.15 * inch))

    # Horizontal rule
    elements.append(_hrule())
    elements.append(Spacer(1, 0.1 * inch))

    # Property info row
    prop_address = address or project_info.get("address", "") or project_info.get("name", "")
    info_data = [
        [
            Paragraph(f"<b>Property:</b> {prop_address or 'See project details'}", styles["InfoText"]),
            Paragraph(f"<b>Homeowner:</b> {homeowner_name or '—'}", styles["InfoText"]),
            Paragraph(f"<b>Claim #:</b> {claim_number or '—'}", styles["InfoText"]),
            Paragraph(f"<b>Inspector:</b> {inspector_name or '—'}", styles["InfoText"]),
        ]
    ]
    info_table = Table(info_data, colWidths=[content_width * 0.35, content_width * 0.22, content_width * 0.18, content_width * 0.25])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_GRAY]),
        ("BOX", (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(info_table)
    return elements


def _build_summary(styles, damage_report: DamageReport):
    elements = [Paragraph("EXECUTIVE SUMMARY", styles["SectionHeading"])]

    sev = damage_report.overall_severity
    sev_color = SEVERITY_COLOR.get(sev, MID_GRAY)

    rows = [
        ["Overall Damage Severity", sev],
        ["Damage Types Identified", ", ".join(damage_report.damage_types) or "None detected"],
        ["Photos Analyzed", f"{damage_report.assessable_photos} of {damage_report.total_photos}"],
    ]

    content_width = PAGE_W - 2 * MARGIN
    t = Table(rows, colWidths=[content_width * 0.38, content_width * 0.62])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (0, -1), WHITE),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (1, 0), (1, -1), [WHITE, LIGHT_GRAY]),
        ("BOX", (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, MID_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        # Color severity cell
        ("TEXTCOLOR", (1, 0), (1, 0), sev_color),
        ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (1, 0), (1, 0), 11),
    ]))
    elements.append(t)
    return elements


def _build_findings_table(styles, damage_report: DamageReport):
    elements = [
        Spacer(1, 0.1 * inch),
        Paragraph("DAMAGE FINDINGS BY PHOTO", styles["SectionHeading"]),
    ]

    assessable = [f for f in damage_report.findings if f.assessable]
    if not assessable:
        elements.append(Paragraph("No assessable photos found.", styles["BodyText"]))
        return elements

    content_width = PAGE_W - 2 * MARGIN
    headers = ["Photo #", "Damage Type", "Severity", "Affected Area"]
    col_widths = [
        content_width * 0.08,
        content_width * 0.27,
        content_width * 0.15,
        content_width * 0.50,
    ]

    rows = [headers]
    for f in assessable:
        rows.append([
            str(f.photo_number),
            f.damage_type or "—",
            f.severity or "—",
            f.affected_area or "—",
        ])

    t = Table(rows, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("BOX", (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, MID_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("WORDWRAP", (0, 0), (-1, -1), True),
    ]
    # Color severity cells
    for i, f in enumerate(assessable, start=1):
        sev_col = SEVERITY_COLOR.get(f.severity, BLACK)
        style_cmds.append(("TEXTCOLOR", (2, i), (2, i), sev_col))
        style_cmds.append(("FONTNAME", (2, i), (2, i), "Helvetica-Bold"))

    t.setStyle(TableStyle(style_cmds))
    elements.append(t)
    return elements


def _build_recommendations(styles, damage_report: DamageReport):
    elements = [
        Spacer(1, 0.1 * inch),
        Paragraph("DAMAGE DOCUMENTATION SUMMARY", styles["SectionHeading"]),
    ]

    sev = damage_report.overall_severity
    sev_color = SEVERITY_COLOR.get(sev, MID_GRAY)

    if sev in ("Severe", "Moderate"):
        detail = (
            "The inspection documented significant storm damage across multiple roof surfaces. "
            "The findings recorded in this report — including impact marks, granule displacement, "
            "displaced or lifted shingles, and soft metal damage — are consistent with damage "
            "resulting from a qualifying weather event. This documentation has been prepared to "
            "provide an accurate, photo-supported record of the roof's current condition. "
            "We encourage the homeowner to review these findings with their insurance carrier "
            "to understand their coverage options."
        )
    elif sev == "Minor":
        detail = (
            "The inspection identified localized storm-related damage to the roof. While the "
            "affected area may appear limited, documented damage of this nature can worsen over "
            "time if left unaddressed. These findings have been recorded as a photo-supported "
            "account of the roof's current condition for the homeowner's records and for review "
            "with their insurance carrier as appropriate."
        )
    else:
        detail = (
            "The inspection was completed and the findings are documented in this report. "
            "The homeowner is encouraged to retain this report for their records."
        )

    elements.append(Paragraph(
        f'<font color="{sev_color.hexval()}"><b>Documented Damage Level: {sev}</b></font>',
        styles["ActionText"]
    ))
    elements.append(Spacer(1, 0.05 * inch))
    elements.append(Paragraph(detail, styles["BodyText"]))

    # Per-photo descriptions
    desc_rows = []
    for f in damage_report.findings:
        if f.assessable and f.description:
            desc_rows.append([
                Paragraph(f"<b>Photo {f.photo_number}</b>", styles["SmallText"]),
                Paragraph(f.description, styles["SmallText"]),
            ])

    if desc_rows:
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph("Detailed Findings:", styles["SubSectionHeading"]))
        content_width = PAGE_W - 2 * MARGIN
        dt = Table(desc_rows, colWidths=[content_width * 0.12, content_width * 0.88])
        dt.setStyle(TableStyle([
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_GRAY]),
            ("BOX", (0, 0), (-1, -1), 0.5, MID_GRAY),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, MID_GRAY),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(dt)

    return elements


def _build_photo_section(styles, damage_report: DamageReport):
    elements = [Paragraph("PHOTO EVIDENCE", styles["SectionHeading"])]

    photos_per_row = 2
    content_width = PAGE_W - 2 * MARGIN
    photo_w = (content_width - 0.25 * inch) / photos_per_row
    photo_h = photo_w * 0.65

    assessable = [f for f in damage_report.findings if f.assessable and f.photo_path.exists()]

    if not assessable:
        elements.append(Paragraph("No photos available.", styles["BodyText"]))
        return elements

    # Group into rows of 2
    for row_start in range(0, len(assessable), photos_per_row):
        row_findings = assessable[row_start: row_start + photos_per_row]
        img_cells = []
        caption_cells = []

        for f in row_findings:
            try:
                img = _fit_image(str(f.photo_path), max_w=photo_w, max_h=photo_h)
                img_cells.append(img)
            except Exception:
                img_cells.append(Paragraph("[Image unavailable]", styles["SmallText"]))

            caption = f'<b>Photo {f.photo_number}</b><br/>{f.damage_type} — {f.affected_area}'
            caption_cells.append(Paragraph(caption, styles["Caption"]))

        # Pad to 2 columns
        while len(img_cells) < photos_per_row:
            img_cells.append("")
            caption_cells.append("")

        col_w = [photo_w + 0.1 * inch] * photos_per_row
        photo_table = Table([img_cells, caption_cells], colWidths=col_w)
        photo_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(KeepTogether([photo_table, Spacer(1, 0.15 * inch)]))

    return elements


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fit_image(path: str, max_w: float, max_h: float) -> Image:
    """Load image and scale to fit within max_w x max_h while preserving aspect ratio."""
    with PILImage.open(path) as img:
        orig_w, orig_h = img.size
    ratio = min(max_w / orig_w, max_h / orig_h)
    return Image(path, width=orig_w * ratio, height=orig_h * ratio)


def _hrule():
    """Thin horizontal rule table."""
    t = Table([[""]], colWidths=[PAGE_W - 2 * MARGIN], rowHeights=[2])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), DARK_BLUE)]))
    return t


def _draw_footer(canvas, doc):
    """Draw page number and company name at bottom of each page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MID_GRAY)
    canvas.drawString(MARGIN, 0.45 * inch, "BEARD ROOFING — Confidential Damage Report")
    canvas.drawRightString(
        PAGE_W - MARGIN, 0.45 * inch, f"Page {doc.page}"
    )
    canvas.restoreState()


def _build_styles():
    base = getSampleStyleSheet()
    styles = {}

    def s(name, **kwargs):
        styles[name] = ParagraphStyle(name, **kwargs)

    s("ReportTitle", fontSize=18, fontName="Helvetica-Bold", textColor=DARK_BLUE, alignment=TA_RIGHT)
    s("CompanyName", fontSize=16, fontName="Helvetica-Bold", textColor=DARK_BLUE)
    s("SubTitle", fontSize=10, fontName="Helvetica", textColor=LIGHT_BLUE, alignment=TA_RIGHT)
    s("SectionHeading", fontSize=11, fontName="Helvetica-Bold", textColor=WHITE,
      backColor=DARK_BLUE, leftIndent=6, rightIndent=6, spaceBefore=8, spaceAfter=4,
      leading=18)
    s("SubSectionHeading", fontSize=10, fontName="Helvetica-Bold", textColor=DARK_BLUE,
      spaceBefore=4, spaceAfter=2)
    s("InfoText", fontSize=9, fontName="Helvetica")
    s("BodyText", fontSize=9, fontName="Helvetica", leading=14, spaceAfter=4)
    s("ActionText", fontSize=12, fontName="Helvetica-Bold", spaceBefore=4, spaceAfter=4)
    s("Caption", fontSize=8, fontName="Helvetica", alignment=TA_CENTER, leading=12)
    s("SmallText", fontSize=8, fontName="Helvetica", leading=11)

    return styles
