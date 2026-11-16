# Interface and brand

## V3 viewer direction

Keep the original PDF as the primary visual reference. Show a one-row OCR status by default; expanded details scroll within a bounded height. The original page, extracted text, and evidence context are separate tabs with labels rather than color alone. Page status explicitly distinguishes native text, missing text, OCR processing, completed OCR, failed OCR, and review recommendations. Preserve green application surfaces and amber evidence highlights.

The active Qt app is branded **Verdant / Disclosure Scorer**. The direction is a calm, structured accounting workpaper: a dark green shell, strong contrast, clear status and totals, and a three-column review layout. It uses Windows Segoe UI for reliable local rendering.

## Palette

| Purpose | Color |
| --- | --- |
| Background | `#101a17` |
| Panel | `#17231e` |
| Raised input | `#1d2b23` |
| Border | `#30473b` |
| Primary action | `#298a56` |
| Progress | `#50b879` |
| Selected item | `#245d42` |
| Main text | `#edf4ef` |
| Secondary text | `#a9bbb0` |

The SVG mark is a small ledger/bar motif. The UI uses text labels for actions so meaning does not rely on icons. Green indicates primary action and progress; a keyword highlight uses amber for visibility within excerpts.

## Layout

- **Header**: brand, project purpose, status indicator, and company/year metadata capped at 54px; overall ESG/SDG score summary badge is positioned in the top-right corner widget of the work tabs.
- **Work tabs**:
  - **PDF reader**: Two-pane horizontal splitter (`reader_splitter_v2`) with a visible 7px divider handle:
    - **Left pane (58% width, min 540px, full vertical height)**: 1-line compact OCR warning strip (~34px) triggering non-intrusive popup `OCRDetailsPopup`, document row, compact 1-row navigation/zoom/OCR toolbar, reader views (**All PDF pages** and **Highlighted page**), and single-line elided footer (`page_label`).
    - **Right pane (42% width, min 420px)**: Scoring item context header, terms with tooltip, criteria score proposal hint, hit list (min 120px, stretch 2), tabbed viewer (**Evidence context** and **Extracted text**, stretch 3), and bottom action buttons (**Pin selected passage**, **Checklist and decisions**).
  - **Checklist and decisions**: Two-pane horizontal splitter (`checklist_splitter_v2`) with searchable rubric checklist on the left and decision scoring/evidence inputs on the right.
  - **Score overview**: Aggregate matrix showing automated vs. manual scores by ESG pillar and SDG goal.

Vertical budgets guarantee that on display scalings down to 1280x720 (150% scaling on 1080p), the PDF viewing area retains >=400px of height, the hit list retains >=120px, and bottom action buttons remain strictly visible above the status bar without clipping or scrolling out of reach.

The design draws on Fluent’s spacing, rounded surfaces, and predictable controls. `PyQt-Fluent-Widgets` is not installed. Its published license has conditions that would need a project decision before adopting it as a dependency.

## V2.1 additions

Header status chip, three metric tiles, labelled panes, a PDF page tab with highlights, and locked/validated decision controls. A page's printed number is shown only when the PDF defines a page label; otherwise the UI says it was not detected.

## Next design milestone

Selectable text layer on the rendered page, Overview and Evidence Registry views, and multi-evidence per item.
