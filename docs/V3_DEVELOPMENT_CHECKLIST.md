# Verdant V3 development checklist

Source: `../../Fixes/Fix# Verdant V3.0 — Complete Developme.txt`. The revised consolidated workbook remains scoring authority. This checklist tracks implementation, not promises.

## Baseline, 2026-11-16

- [x] Read current README, QA, changelog, design, runbook, architecture, and context documents; inspect active Qt, scoring, OCR, storage, tests, and build script.
- [x] Baseline: 24 tests pass. Runtime has 81 rubric decisions and 60 workbook company names.
- [x] Backed up SQLite with its online backup API to `data/backups/pdf_scorer_before_v3_20261116_164035.db`; integrity check returned `ok`.
- [x] Existing: native PDF rendering, OCR of pages without text, keyword/partial OCR highlights, proposed 30/102 totals, manual decisions, workspaces, SQLite plus CSV.
- [x] Phase 1 core: compact persistent OCR warning, original PDF navigation independent of search/OCR, three viewer modes, per-page status, selective OCR, safe stop between pages, zoom/page jump, bounded rendered-page cache.
- [ ] Phase 1 remaining: background page rendering for unusually complex PDFs; optional thumbnails; selectable text overlay on image pages; live OCR accuracy/performance audit on company reports.
- [ ] Phase 2: full navigation, dashboard, workspace filters, display scaling audit.
- [ ] Phase 3: multiple-evidence registry and safe schema migration.
- [ ] Phase 4: improve scoring rules and measure accuracy on annotated company reports.
- [ ] Phase 5: audit interface and reviewer sign-off.
- [ ] Phase 6: structured research exports.
- [ ] Phase 7: backup/restore UI, settings, diagnostics, research roster inclusion flags.
- [ ] Phase 8: decouple Qt core from legacy Tk imports where safe.
- [ ] Phase 9: release QA, PyInstaller build and clean-machine verification.
- [ ] Phase 10: documentation and handoff.

## Source contradictions

Historical V2 documents contain phase-specific claims that OCR and page rendering were absent; the current source implements both. The V3 phase-1 work therefore extends the existing reader rather than replacing it. `Final Scoring.pdf` remains historical where it differs from the revised workbook.

## Current implementation plan

1. Finish and test visible import/scoring progress, score summary, and current-item PDF highlights already in progress.
2. Make OCR warnings compact and persistent, with page counts and navigation to missing-text pages.
3. Let reviewers open any imported PDF page before OCR; add page jump, zoom, and viewer modes.
4. Add selective OCR and clear per-page processing states while keeping the original PDFs unchanged.
5. Run focused and full tests, update README/QA/changelog, and record remaining V3 phases as pending.
