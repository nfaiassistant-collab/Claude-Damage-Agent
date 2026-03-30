# Beard Roofing — AI Damage Report Generator

## What This Is
Automated roof damage report generator for Beard Roofing & Exteriors.
Pulls inspection photos from CompanyCam → Claude Code analyzes damage →
generates a professional PDF evidence report for homeowners.

**Contractor:** Noah Farmer (inspector / roofing contractor)
**Company:** Beard Roofing & Exteriors

---

## Workflow (Three Phases)

### Phase 1 — Download Photos
```bash
python main.py download --share-link "https://app.companycam.com/galleries/XXXXX"
```
Downloads all photos to `temp_photos/`, writes `manifest.json`.

### Phase 2 — Analyze Photos (Claude Code in-session)
After download, ask Claude Code:
> "Please analyze the roof photos in temp_photos/ using the manifest and write findings.json"

Claude reads each photo, identifies damage, writes `temp_photos/findings.json`.
**Important:** Use the Agent subagent tool to avoid context window overflow on large sets (80+ photos).
The agent gets its own isolated context window, reads all photos, and writes findings.json without polluting the main session.

### Phase 3 — Generate PDF
```bash
python main.py generate \
  --address "123 Main St, City, State ZIP" \
  --homeowner "Jane Smith" \
  --inspector "Noah Farmer"
```
Output PDF saved to `reports/`.

---

## Photo Curation (photo_selection.json)
After analysis, Claude curates which photos to include and in what order.
Saved to `temp_photos/photo_selection.json`. Edit to add/remove/reorder before generating.

**Standard ordering:**
1. **Overview shots** — whole slopes showing test squares (TurboGuard mats first — strongest evidence)
2. **Severe individual damage** — chalk-marked hail bruises, blown shingles (Severe-rated only)
3. **Corroborating damage** — soft metal (box vents, pipe boots), gutters, downspouts, fascia, chimney

**Omit:** redundant similar shots, Moderate-only shingle photos, company logos, blank/failed images

---

## Roofing Domain Expertise

### Chalk Notation (Inspector Markings)
| Mark | Meaning |
|------|---------|
| Circle | Hail impact / bruise location |
| Line | Wind crease or lifted shingle |
| F=10+H | Front slope, 10+ hail hits in test square |
| R=10+H | Rear slope, 10+ hail hits |
| L=10+H | Left slope, 10+ hail hits |
| RL=3W | Ridge line, 3 wind-damaged shingles |

### Test Squares
TurboGuard test mats placed on slopes to objectively document hail impact count and size.
Photos of test mats are the strongest evidence — always include these first in the report.

### Damage Types
- **Hail Damage**: Circular bruises, granule displacement, exposed mat (fiberglass backing visible = severe)
- **Wind Damage**: Creased/lifted tabs, chalk lines, blow-off shingles photographed face-down showing Atlas sealant strip failure
- **Soft Metal Damage**: Dents on box vents, pipe boot collars, gutters, drip edge — corroborates hail size
- **Structural Damage**: Chimney mortar spalling, cracked cap — often corroborating evidence

### Key Evidence Photos to Prioritize
- **Test mat photos**: Objective hit count — always lead with these
- **Back-of-shingle**: Shows Atlas sealant strip, confirms wind blow-off
- **Mat exposure close-ups**: Granule loss down to fiberglass = severe hail bruise
- **Gutter granule accumulation**: Confirms widespread granule loss from hail
- **Soft metal dents**: Box vents, pipe boots, gutters with tape measure if available

---

## Report Philosophy
We present documented evidence. We do **not**:
- Recommend full replacement (that is the adjuster's job)
- Explicitly advise homeowners to file claims

We **do**:
- Document damage objectively with photos
- Note that findings are "consistent with a qualifying weather event"
- Encourage homeowners to "review findings with their insurance carrier to understand their coverage options"

---

## File Structure
| File | Purpose |
|------|---------|
| `main.py` | CLI entry point — `download` and `generate` subcommands |
| `companycam_scraper.py` | Playwright scraper for CompanyCam public share galleries |
| `report_parser.py` | Reads existing PDFs from Damage Reports folder to extract template structure |
| `report_generator.py` | ReportLab PDF builder — header, summary, photo grid |
| `damage_analyzer.py` | `PhotoFinding` / `DamageReport` dataclasses + JSON serialization |
| `config.py` | Loads `.env` settings, auto-creates output dirs |
| `temp_photos/` | Downloaded photos + JSON metadata (gitignored — not committed) |
| `reports/` | Generated PDFs (gitignored — not committed) |

### Key JSON Files (in temp_photos/, not committed)
| File | Written by | Purpose |
|------|-----------|---------|
| `manifest.json` | `main.py download` | List of all downloaded photo paths |
| `findings.json` | Claude Code (agent) | Per-photo damage analysis results |
| `photo_selection.json` | Claude Code (curated) | Ordered list of photo numbers to include in PDF |

---

## Configuration (.env)
```
DAMAGE_REPORTS_DIR=C:\Users\nwfar\Downloads\Damage Reports
COMPANY_LOGO_PATH=C:\Users\nwfar\Downloads\Damage Reports\Beard Logo.png
OUTPUT_DIR=C:\Users\nwfar\Desktop\ClaudeCodeTest\reports
```

---

## Setup (New Machine)
```bash
pip install -r requirements.txt
playwright install chromium
```
Copy `.env` with correct local paths before running.

---

## Context Window Management
- Analyzing 80+ photos in one session will overflow context and lose results
- Always use the **Agent subagent** for photo analysis: it runs in an isolated context, writes findings.json, returns a summary
- The main session never needs to see individual photo analysis — only the final findings.json

---

## Continuous Improvement Log

### Completed
- Switched from paid Anthropic API to Claude Pro in-session vision (zero API cost)
- Playwright scraper replaces CompanyCam API key requirement
- Agent subagent isolation solves context overflow for large photo sets
- photo_selection.json enables curated, ordered photo sets per job
- Report no longer makes replacement recommendations — presents evidence only
- Homeowner field added to report header

### Known Areas to Improve
- Photo captions could include inspector chalk notation (F=10+H) alongside damage type
- Executive summary could include date of storm / date of inspection as separate fields
- photo_selection.json curation could be further automated by grouping photos by slope/facet
- Consider adding a signature/certification statement at the end
- Explore adding a cover page with property photo (aerial or street view)
- Add storm date lookup by cross-referencing inspection date with NOAA storm data
