"""
Roof Damage Report Agent — CLI Entry Point

Two-phase workflow:

  Phase 1 — Download photos from CompanyCam:
    python main.py --download --share-link "https://app.companycam.com/galleries/..."

  Phase 2 — Generate PDF from findings written by Claude Code:
    python main.py --generate --findings temp_photos/findings.json \
                   --address "123 Main St" --claim "CLAIM-001" --inspector "John Smith"
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from config import OUTPUT_DIR, TEMP_PHOTOS_DIR
from companycam_scraper import scrape_project
from report_parser import load_template
from damage_analyzer import load_findings
from report_generator import generate_report


def cmd_download(args):
    """Phase 1: scrape CompanyCam and download all photos."""
    print("=" * 60)
    print("  PHASE 1 — DOWNLOAD PHOTOS")
    print("=" * 60)

    print("\nFetching photos from CompanyCam...")
    photo_paths, project_info = scrape_project(args.share_link)

    if not photo_paths:
        print("\nERROR: No photos downloaded. Check the share link and try again.")
        sys.exit(1)

    print(f"  Project : {project_info.get('name', 'Unknown')}")
    print(f"  Photos  : {len(photo_paths)} downloaded to {TEMP_PHOTOS_DIR}")

    # Write manifest so Claude Code knows what to analyze
    manifest = {
        "project_info": project_info,
        "share_link": args.share_link,
        "photo_paths": [str(p) for p in photo_paths],
        "total_photos": len(photo_paths),
    }
    manifest_path = TEMP_PHOTOS_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"\nManifest written to: {manifest_path}")
    print("\n" + "=" * 60)
    print("  NEXT STEP:")
    print("  Ask Claude Code to analyze the photos:")
    print('  "Please analyze the roof photos in the manifest and write findings.json"')
    print("=" * 60)


def cmd_generate(args):
    """Phase 2: load findings.json written by Claude Code and generate PDF."""
    print("=" * 60)
    print("  PHASE 2 — GENERATE PDF REPORT")
    print("=" * 60)

    findings_path = Path(args.findings)
    if not findings_path.exists():
        print(f"\nERROR: Findings file not found: {findings_path}")
        print("Run Phase 1 first, then ask Claude Code to analyze the photos.")
        sys.exit(1)

    # Load project info from manifest if available
    manifest_path = TEMP_PHOTOS_DIR / "manifest.json"
    project_info = {}
    if manifest_path.exists():
        project_info = json.loads(manifest_path.read_text()).get("project_info", {})

    print("\nLoading AI findings...")
    damage_report = load_findings(findings_path)

    print(f"  Overall Severity:        {damage_report.overall_severity}")
    print(f"  Replacement Recommended: {'YES' if damage_report.replacement_recommended else 'No'}")
    print(f"  Damage Types Found:      {', '.join(damage_report.damage_types) or 'None'}")
    print(f"  Photos Assessed:         {damage_report.assessable_photos}/{damage_report.total_photos}")

    print("\nLoading report template from existing damage reports...")
    template = load_template()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = _safe_filename(args.address or project_info.get("name", "inspection"))
    output_path = output_dir / f"damage_report_{safe_name}_{timestamp}.pdf"

    print("\nGenerating PDF...")
    selection_path = TEMP_PHOTOS_DIR / "photo_selection.json"
    generate_report(
        damage_report=damage_report,
        template=template,
        project_info=project_info,
        output_path=output_path,
        property_address=args.address,
        claim_number=args.claim,
        inspector_name=args.inspector,
        homeowner_name=args.homeowner,
        photo_selection_path=selection_path if selection_path.exists() else None,
    )

    print("\n" + "=" * 60)
    print("  DONE! Report saved to:")
    print(f"  {output_path}")
    print("=" * 60)


def _safe_filename(name: str) -> str:
    import re
    safe = re.sub(r"[^\w\s-]", "", name)
    safe = re.sub(r"\s+", "_", safe.strip())
    return safe[:40] or "report"


def main():
    parser = argparse.ArgumentParser(
        description="Roof Damage Report Agent"
    )
    sub = parser.add_subparsers(dest="command")

    # ── download subcommand ───────────────────────────────────────────────────
    dl = sub.add_parser("download", help="Phase 1: download photos from CompanyCam")
    dl.add_argument("--share-link", "-l", required=True,
                    help="CompanyCam share link")

    # ── generate subcommand ───────────────────────────────────────────────────
    gen = sub.add_parser("generate", help="Phase 2: generate PDF from findings.json")
    gen.add_argument("--findings", "-f",
                     default=str(TEMP_PHOTOS_DIR / "findings.json"),
                     help="Path to findings.json written by Claude Code")
    gen.add_argument("--output", "-o", default=str(OUTPUT_DIR),
                     help="Output folder for generated PDF")
    gen.add_argument("--address", "-a", default="", help="Property address")
    gen.add_argument("--homeowner", "-w", default="", help="Homeowner name")
    gen.add_argument("--claim", "-c", default="", help="Claim or job number")
    gen.add_argument("--inspector", "-i", default="", help="Inspector name")

    # ── legacy single-command support (--share-link at top level) ────────────
    parser.add_argument("--share-link", "-l", default=None)
    parser.add_argument("--output", "-o", default=str(OUTPUT_DIR))
    parser.add_argument("--address", "-a", default="")
    parser.add_argument("--homeowner", "-w", default="")
    parser.add_argument("--claim", "-c", default="")
    parser.add_argument("--inspector", "-i", default="")

    args = parser.parse_args()

    if args.command == "download":
        cmd_download(args)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.share_link:
        # Legacy: --download is implied
        args.command = "download"
        cmd_download(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
