"""
Damage analyzer — data structures and JSON serialization.

The AI analysis is performed by Claude Code directly (reading images in-session).
This module provides:
  - PhotoFinding / DamageReport dataclasses
  - save_findings()  — write findings to JSON after Claude Code analysis
  - load_findings()  — read findings JSON to produce DamageReport for PDF generation
"""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PhotoFinding:
    photo_path: Path
    photo_number: int
    damage_type: str = ""
    severity: str = ""
    affected_area: str = ""
    description: str = ""
    replacement_recommended: str = ""
    notes: str = ""
    assessable: bool = True


@dataclass
class DamageReport:
    findings: list[PhotoFinding] = field(default_factory=list)
    overall_severity: str = ""
    damage_types: list[str] = field(default_factory=list)
    replacement_recommended: bool = False
    total_photos: int = 0
    assessable_photos: int = 0


# ── JSON schema written by Claude Code ────────────────────────────────────────
#
# findings.json format:
# {
#   "overall_severity": "Severe",
#   "replacement_recommended": true,
#   "damage_types": ["Hail Damage", "Wind Damage"],
#   "total_photos": 102,
#   "assessable_photos": 98,
#   "findings": [
#     {
#       "photo_number": 1,
#       "photo_path": "C:/.../.../photo_001.jpg",
#       "damage_type": "Hail Damage",
#       "severity": "Severe",
#       "affected_area": "Field Slope",
#       "description": "...",
#       "replacement_recommended": "Yes",
#       "notes": "10+ hail hits noted by inspector (F=10+H)",
#       "assessable": true
#     },
#     ...
#   ]
# }


def save_findings(findings_path: Path, report: DamageReport):
    """Serialize a DamageReport to findings.json."""
    data = {
        "overall_severity": report.overall_severity,
        "replacement_recommended": report.replacement_recommended,
        "damage_types": report.damage_types,
        "total_photos": report.total_photos,
        "assessable_photos": report.assessable_photos,
        "findings": [
            {
                "photo_number": f.photo_number,
                "photo_path": str(f.photo_path),
                "damage_type": f.damage_type,
                "severity": f.severity,
                "affected_area": f.affected_area,
                "description": f.description,
                "replacement_recommended": f.replacement_recommended,
                "notes": f.notes,
                "assessable": f.assessable,
            }
            for f in report.findings
        ],
    }
    findings_path.write_text(json.dumps(data, indent=2))
    print(f"Findings saved to: {findings_path}")


def load_findings(findings_path: Path) -> DamageReport:
    """Load a findings.json file into a DamageReport."""
    data = json.loads(findings_path.read_text())

    findings = [
        PhotoFinding(
            photo_number=f["photo_number"],
            photo_path=Path(f["photo_path"]),
            damage_type=f.get("damage_type", ""),
            severity=f.get("severity", ""),
            affected_area=f.get("affected_area", ""),
            description=f.get("description", ""),
            replacement_recommended=f.get("replacement_recommended", ""),
            notes=f.get("notes", ""),
            assessable=f.get("assessable", True),
        )
        for f in data.get("findings", [])
    ]

    return DamageReport(
        findings=findings,
        overall_severity=data.get("overall_severity", ""),
        damage_types=data.get("damage_types", []),
        replacement_recommended=data.get("replacement_recommended", False),
        total_photos=data.get("total_photos", len(findings)),
        assessable_photos=data.get("assessable_photos", sum(1 for f in findings if f.assessable)),
    )
