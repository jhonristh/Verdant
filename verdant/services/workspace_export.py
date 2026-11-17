"""A readable Excel snapshot of one company-year workpaper."""
import os
import tempfile
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


GREEN = PatternFill("solid", fgColor="173B2B")
PALE = PatternFill("solid", fgColor="E9F5EC")
AMBER = PatternFill("solid", fgColor="FFF1CF")
GRAY = PatternFill("solid", fgColor="EFF2EF")


def _safe(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _header(sheet, labels, widths):
    sheet.append(labels)
    sheet.freeze_panes = "C2" if len(labels) > 8 else "A2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(labels))}1"
    for column, width in enumerate(widths, 1):
        sheet.column_dimensions[get_column_letter(column)].width = width
    for cell in sheet[1]:
        cell.fill = GREEN
        cell.font = Font(name="Aptos", bold=True, color="FFFFFF")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    sheet.row_dimensions[1].height = 32


def _detail_row(sheet, values, state=None):
    sheet.append([_safe(value) for value in values])
    row = sheet.max_row
    sheet.row_dimensions[row].height = 30
    for cell in sheet[row]:
        cell.alignment = Alignment(vertical="top", wrap_text=True)
    if state == "supported":
        sheet.cell(row, 5).fill = PALE
    elif state == "review":
        sheet.cell(row, 5).fill = AMBER
    elif state == "unsupported":
        sheet.cell(row, 5).fill = GRAY


def export_workspace_workbook(store, project_id, items, destination):
    """Export only the selected workspace; unsaved leads remain visibly separate."""
    info = store.project_info(project_id)
    if not info:
        raise ValueError("Open a valid company-year workpaper before exporting.")
    company, fiscal_year = info
    records = store.score_records(project_id)
    leads = store.predictions(project_id)
    pins = store.evidence_pins(project_id)
    book = Workbook()
    summary = book.active
    summary.title = "Summary"
    summary.column_dimensions["A"].width = 30
    summary.column_dimensions["B"].width = 66
    summary.append(["VERDANT WORKPAPER", ""])
    for cell in summary[1]:
        cell.fill = GREEN
        cell.font = Font(name="Aptos", bold=True, color="FFFFFF", size=15)
    summary.row_dimensions[1].height = 31
    esg = [item for item in items if item["kind"] == "ESG"]
    sdg = [item for item in items if item["kind"] == "SDG"]
    summary_rows = [
        ("Company", company), ("Fiscal year", fiscal_year),
        ("Reviewed items", f"{len(records)} / {len(items)}"),
        ("ESG confirmed points", f"{sum(records[item['id']]['score'] for item in esg if item['id'] in records)} / {sum(item['weight'] for item in esg)}"),
        ("SDG confirmed points", f"{sum(records[item['id']]['score'] * item['weight'] for item in sdg if item['id'] in records)} / {sum(item['weight'] for item in sdg)}"),
        ("Pinned passages", len(pins)),
        ("Lead search", "Available" if leads else "Not run or invalidated"),
        ("Scorer", store.setting("scorer_name", "")),
        ("Review rule", "Only saved manual decisions count. Leads are suggestions for inspection."),
    ]
    for label, value in summary_rows:
        summary.append([label, _safe(value)])
        summary.cell(summary.max_row, 1).font = Font(bold=True, color="173B2B")
        summary.cell(summary.max_row, 2).alignment = Alignment(wrap_text=True, vertical="center")
        summary.row_dimensions[summary.max_row].height = 28

    decisions = book.create_sheet("Decisions")
    _header(decisions, ["Framework", "Category", "Criterion", "Weight", "Saved decision", "Confirmed points",
                        "Lead result", "Lead confidence", "Lead reason", "Best hit document", "Best hit PDF page",
                        "Evidence document", "PDF page(s)", "Printed page(s)", "Reviewer note", "Updated at"],
            [14, 20, 56, 11, 19, 18, 20, 17, 65, 42, 18, 42, 20, 20, 70, 24])
    for item in items:
        code = item["id"]
        saved = records.get(code)
        lead = leads.get(code)
        best = (lead.get("hits") or [None])[0] if lead else None
        decision = "Not reviewed" if saved is None else "Supported" if saved["score"] else "Not supported"
        lead_result = "Not checked" if lead is None else "Lead found" if lead["suggestion"] else "Hit needs review" if lead["hits"] else "No text hit"
        _detail_row(decisions, [item["kind"], code, item["title"], item["weight"], decision,
                                saved["score"] * item["weight"] if saved else None,
                                lead_result, lead.get("confidence") if lead else None,
                                lead.get("reason") if lead else None,
                                best.get("document") if best else None, best.get("page") if best else None,
                                saved.get("document") if saved else None, saved.get("pages") if saved else None,
                                saved.get("printed_pages") if saved else None,
                                saved.get("evidence") if saved else None,
                                saved.get("updated_at") if saved else None],
                    "supported" if saved and saved["score"] else "unsupported" if saved else "review")
    decisions.auto_filter.ref = f"A1:P{decisions.max_row}"

    evidence = book.create_sheet("Evidence pins")
    _header(evidence, ["Category", "Document", "PDF page", "Printed page", "Pinned passage", "Pinned at"],
            [20, 48, 16, 18, 100, 24])
    for pin in pins:
        _detail_row(evidence, [pin["item_id"], pin["document"], pin["page"],
                               pin["printed_page"] or None, pin["excerpt"], pin["created_at"]])
    evidence.auto_filter.ref = f"A1:F{max(1, evidence.max_row)}"

    output = Path(destination).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".verdant_export_", suffix=".xlsx", dir=output.parent)
    os.close(handle)
    try:
        book.save(temporary)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return output
