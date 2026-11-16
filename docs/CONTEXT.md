# Project context

## Purpose

Verdant Disclosure Scorer supports a research study of ESG and SDG disclosures by industrial publicly listed companies in the Philippines. A reviewer opens a company and fiscal year, imports annual/sustainability/SEC report PDFs, searches checklist terms, reads context, records a 0 or 1 decision, and exports a traceable score sheet.

Keyword matches are leads, not automatic awards. A supported score needs company-specific evidence beyond a generic mention. The reviewer records the source document, PDF page reference, and excerpt. The fiscal year is the period covered by the report, not necessarily its publication year.

## Scoring authority

The team chose the **revised workbook** as the scoring authority where it differs from `Final Scoring.pdf`.

- ESG: 30 binary statements, E1–E10, S1–S10, G1–G10; maximum 30.
- SDG: 17 goals with Identified (1 point), Managed (2), Reported (3); maximum 6 per goal and 102 overall.
- Managed can be supported only when Identified is supported. Reported requires Managed. Removing an earlier stage is blocked while a later stage remains supported.
- The rubric in `scoring_rubric.json` reflects the workbook’s revised ESG statements and search terms.

The PDF describes 51 SDG points and some different Social statements. Do not mix its scores into the revised workbook model without a deliberate conversion.

## Company and year scope

`ESG_SDG_Scoring_Consolidated.xlsx`, in this application root, supplies the `Companies` sheet. The app reads 60 unique company names and offers fiscal years 2022, 2023, 2024, and 2025. The user previously specified 58 companies to treat. Which two of the workbook’s 60 are excluded has not been resolved; the selector currently shows all 60.

## Source files

- `../ESG_SDG_Scoring_Consolidated.xlsx`: revised rubric and company roster in the Verdant root.
- `../Final Scoring.pdf`: original methodology reference; not the current SDG weighting authority.
- `../# Summary of the PDF.txt`: explanatory summary of the original PDF.
- `scoring_rubric.json`: runtime search terms and weights.

## Current boundaries

Local single-user prototype. The Google Sheets cloud sync discussed earlier has not been built. Image-only PDF pages can now be OCRed on demand and cached; original scanned PDFs remain unchanged. The Qt reader shows extracted passages and a rendered PDF page. Exports are one flat Scores worksheet, not a full audit pack. There is no sign-off or reviewer locking yet.
The v2.1 Qt reader also renders the selected PDF page. Check for score now generates provisional 0/1 predictions and separate proposed totals; the reviewer must inspect and save final binary decisions. A no-hit proposal of 0 has low confidence and must not be treated as proof of absence. This folder uses its own local SQLite database rather than the shared AppData database.
