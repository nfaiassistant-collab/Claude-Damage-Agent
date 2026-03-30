# Beard Roofing — AI Damage Report Generator

> **Session habit:** At the end of every working session, ask Claude:
> "Update CLAUDE.md with anything new from this session, then commit and push to GitHub."
> This keeps the project memory current automatically.

---

## What This Is
Automated roof damage report generator for Beard Roofing & Exteriors.
Pulls inspection photos from CompanyCam → Claude Code analyzes damage →
generates a professional PDF evidence report for homeowners.

**Contractor / Inspector:** Noah Farmer
**Homeowner field:** Always the property owner (not the inspector)
**Company:** Beard Roofing & Exteriors
**GitHub:** https://github.com/nfaiassistant-collab/Claude-Damage-Agent

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

**Target size:** ~40 photos per report. Quality over quantity.

---

## Report Format (Finalized Decisions)

### What's in the PDF
1. **Header** — Beard logo, "ROOF DAMAGE REPORT", inspection date
2. **Property bar** — Property address | Homeowner | Claim # | Inspector
3. **Executive Summary** — Damage severity, damage types identified, photos analyzed
4. **Photo grid** — 2 photos per row, simple caption below each

### What's NOT in the PDF (removed)
- "Replacement Recommended" field — adjuster's job, not ours
- "Damage Findings by Photo" table — too verbose
- "Recommendations" section — replaced with evidence-only language
- Detailed per-photo description text blocks

### Caption Format
`Photo N`
`Damage Type — Affected Area`
Example: `Photo 36 / Hail Damage — Field Slope`

### Language Guardrails
- Do NOT say "replacement recommended"
- Do NOT say "file a claim"
- DO say "consistent with a qualifying weather event"
- DO say "review with your insurance carrier to understand your coverage options"

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
- **Structural Damage**: Chimney mortar spalling, cracked cap — corroborating evidence

### Key Evidence Photos to Prioritize
- **Test mat photos**: Objective hit count — always lead with these
- **Back-of-shingle**: Shows Atlas sealant strip, confirms wind blow-off
- **Mat exposure close-ups**: Granule loss down to fiberglass = severe hail bruise
- **Gutter granule accumulation**: Confirms widespread granule loss from hail
- **Soft metal dents**: Box vents, pipe boots, gutters with tape measure if available

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
Git credentials: run `git push` once in terminal — browser will pop up to authenticate GitHub. Saves automatically after that.

---

## Context Window Management
- Analyzing 80+ photos in one session will overflow context and lose results
- Always use the **Agent subagent** for photo analysis: it runs in an isolated context, writes findings.json, returns a summary
- The main session never needs to see individual photo analysis — only the final findings.json
- If the session gets compacted (/compact), findings.json on disk is safe — analysis is never lost

---

## Git Workflow (end of each session)
```bash
git add -A
git commit -m "brief description of what changed"
git push
```
Credentials are saved via Git Credential Manager — no token needed after initial setup.

---

## Reference Job (First Complete Run — March 30, 2026)
- **Homeowner:** Marilyn Fite
- **Address:** 3527 NE Shadeland Rd, Marion, Indiana 46952
- **Inspector:** Noah Farmer
- **CompanyCam link:** https://app.companycam.com/galleries/BwYAVQQf
- **Photos:** 102 downloaded, 99 assessable, 41 selected for report
- **Findings:** Severe — Hail Damage, Wind Damage, Soft Metal Damage, Structural Damage
- **No claim number**

---

## Continuous Improvement Log

### Completed (Session 1 — March 30, 2026)
- Switched from paid Anthropic API to Claude Pro in-session vision (zero API cost)
- Playwright scraper replaces CompanyCam API key requirement
- Agent subagent isolation solves context overflow for large photo sets
- photo_selection.json enables curated, ordered photo sets per job (~40 photos)
- Report format finalized: header + summary + photo grid only (no verbose tables)
- Removed replacement recommendations — evidence-only language
- Homeowner field added to report header (separate from inspector)
- Simplified photo captions to "Damage Type — Affected Area"
- Project pushed to GitHub: https://github.com/nfaiassistant-collab/Claude-Damage-Agent
- Git Credential Manager configured — no more manual token pasting

### Known Areas to Improve
- Photo captions could include inspector chalk notation (F=10+H) alongside damage type
- Executive summary could include storm date / inspection date as separate fields
- photo_selection.json curation could group photos by slope/facet automatically
- Consider adding a signature/certification statement at the end of the report
- Explore adding a cover page with property aerial or street view photo
- Add storm date lookup by cross-referencing inspection date with NOAA storm data
- Investigate whether CompanyCam API (if user gets key) would be faster than Playwright scraping
