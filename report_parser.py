"""
Parses existing PDF damage reports to extract their structure,
sections, and style so we can match the format in generated reports.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

from config import DAMAGE_REPORTS_DIR


@dataclass
class ReportTemplate:
    """Structure extracted from existing damage report PDFs."""
    sections: list[str] = field(default_factory=list)       # ordered section headings found
    fields: dict[str, list[str]] = field(default_factory=dict)  # section -> list of field labels
    sample_text: dict[str, str] = field(default_factory=dict)   # section -> example text
    raw_text: str = ""


# Common section headings found in roofing damage reports
KNOWN_SECTIONS = [
    "property information", "property info", "insured", "claimant",
    "roof summary", "roof information", "roof details",
    "damage findings", "damage assessment", "damage summary",
    "hail damage", "wind damage", "storm damage",
    "photo evidence", "photos", "photo documentation",
    "recommendations", "recommendation",
    "estimate", "scope of work",
    "notes", "additional notes", "comments",
    "inspector", "adjuster", "date of inspection",
]


def load_template() -> ReportTemplate:
    """
    Read all PDFs from DAMAGE_REPORTS_DIR and build a ReportTemplate
    by finding common sections and field labels.
    """
    if not DAMAGE_REPORTS_DIR.exists():
        print(f"Warning: Damage Reports folder not found at {DAMAGE_REPORTS_DIR}")
        return _default_template()

    pdf_files = list(DAMAGE_REPORTS_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"Warning: No PDF files found in {DAMAGE_REPORTS_DIR}")
        return _default_template()

    print(f"Parsing {len(pdf_files)} existing report(s) for template structure...")

    all_sections: list[str] = []
    all_fields: dict[str, list[str]] = {}
    all_text = ""

    for pdf_path in pdf_files:
        try:
            template = _parse_single_pdf(pdf_path)
            all_text += template.raw_text + "\n"
            for section in template.sections:
                if section not in all_sections:
                    all_sections.append(section)
            for section, fields in template.fields.items():
                if section not in all_fields:
                    all_fields[section] = []
                for f in fields:
                    if f not in all_fields[section]:
                        all_fields[section].append(f)
        except Exception as e:
            print(f"  Warning: could not parse {pdf_path.name}: {e}")

    if not all_sections:
        return _default_template()

    print(f"  Found sections: {', '.join(all_sections)}")
    return ReportTemplate(
        sections=all_sections,
        fields=all_fields,
        raw_text=all_text,
    )


def _parse_single_pdf(pdf_path: Path) -> ReportTemplate:
    """Extract sections and fields from a single PDF."""
    sections = []
    fields: dict[str, list[str]] = {}
    full_text = ""
    current_section = "General"

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text += text + "\n"

            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue

                # Detect section headings
                detected = _detect_section(line)
                if detected:
                    current_section = detected
                    if current_section not in sections:
                        sections.append(current_section)
                    if current_section not in fields:
                        fields[current_section] = []
                    continue

                # Detect field labels (lines ending with : or containing : early)
                field_label = _detect_field_label(line)
                if field_label and current_section:
                    if current_section not in fields:
                        fields[current_section] = []
                    if field_label not in fields[current_section]:
                        fields[current_section].append(field_label)

    return ReportTemplate(sections=sections, fields=fields, raw_text=full_text)


def _detect_section(line: str) -> str | None:
    """Return normalized section name if line looks like a section heading."""
    lower = line.lower().strip(":.#-_ ")
    for known in KNOWN_SECTIONS:
        if known in lower and len(line) < 60:
            # Title-case the match for display
            return line.strip(":.#-_ ").title()
    # Also detect ALL CAPS lines as likely headings
    if line.isupper() and 3 < len(line) < 60 and not re.search(r"\d{3,}", line):
        return line.title()
    return None


def _detect_field_label(line: str) -> str | None:
    """Return field label if line matches 'Label: value' pattern."""
    match = re.match(r"^([A-Za-z][A-Za-z0-9 /()]{1,40}):\s*.{0,80}$", line)
    if match:
        return match.group(1).strip()
    return None


def _default_template() -> ReportTemplate:
    """Fallback template if no existing PDFs are found."""
    sections = [
        "Property Information",
        "Roof Summary",
        "Damage Findings",
        "Photo Evidence",
        "Recommendations",
        "Notes",
    ]
    fields = {
        "Property Information": ["Property Address", "Claim Number", "Date of Inspection", "Inspector Name"],
        "Roof Summary": ["Roof Type", "Roof Age", "Overall Condition", "Damage Severity"],
        "Damage Findings": ["Damage Type", "Affected Area", "Severity", "Description"],
        "Recommendations": ["Action Required", "Urgency", "Estimated Scope"],
        "Notes": ["Additional Comments"],
    }
    return ReportTemplate(sections=sections, fields=fields)
