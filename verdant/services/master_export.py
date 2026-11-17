"""Export reviewer decisions in the consolidated workbook's paste layout."""
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from verdant.config import ROSTER_PATHS

YEARS = ("2022", "2023", "2024", "2025")
ESG_IDS = tuple(f"{pillar}{number}" for pillar in "ESG" for number in range(1, 11))
STAGES = ("Identified", "Managed", "Reported")


def roster_rows(path=None):
    source = Path(path) if path else next((p for p in ROSTER_PATHS if p.exists()), None)
    if source is None:
        raise FileNotFoundError("The company roster workbook is missing.")
    book = load_workbook(source, read_only=True, data_only=True)
    try:
        rows = []
        for number, ticker, company in book["Companies"].iter_rows(min_row=4, max_col=3, values_only=True):
            if isinstance(company, str) and company.strip() and isinstance(number, (int, float)):
                rows.append((int(number), str(ticker or ""), company.strip()))
        return sorted(rows, key=lambda row: row[0])
    finally:
        book.close()


def _header(sheet, title, headings):
    sheet.append([title])
    sheet.append(["Company-year decisions start on row 4; blank means unreviewed."])
    sheet.append(headings)
    sheet.freeze_panes = "E4"
    sheet.auto_filter.ref = f"A3:{get_column_letter(len(headings))}3"
    sheet.row_dimensions[3].height = 28
    for cell in sheet[3]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="214B37")
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for column, width in {"A": 9, "B": 17, "C": 36, "D": 13}.items():
        sheet.column_dimensions[column].width = width


def build_master_export(store, roster_path=None):
    """Create a new workbook. Never change the reference/master workbook."""
    roster = roster_rows(roster_path)
    projects = {(company.casefold(), str(year)): project_id for project_id, company, year in store.projects()}
    known = {company.casefold() for _, _, company in roster}
    extras = sorted({company for _, company, _ in store.projects() if company.casefold() not in known})
    roster += [(len(roster) + index, "", company) for index, company in enumerate(extras, 1)]

    book = Workbook()
    esg = book.active; esg.title = "ESG_Scores"
    sdg = book.create_sheet("SDG_Scores")
    evidence = book.create_sheet("Evidence_Log")
    readme = book.create_sheet("README")
    _header(esg, "ESG scoring - master workbook layout",
            ["Co. #", "Ticker", "Company", "Fiscal year", *ESG_IDS,
             "E total (of 10)", "S total (of 10)", "G total (of 10)",
             "ESG total (of 30)", "E score (0-100)", "S score (0-100)", "G score (0-100)"])
    sdg_headers = ["Co. #", "Ticker", "Company", "Fiscal year"]
    for _ in range(17):
        sdg_headers.extend((*STAGES, "Points (max 6)"))
    sdg_headers.extend(("SDG points (of 102)", "SDG score (0-100)"))
    _header(sdg, "SDG scoring - master workbook layout", sdg_headers)
    _header(evidence, "Evidence log - one row per supported item",
            ["Ticker", "Fiscal year", "Framework", "Item", "Document name", "Page(s)",
             "Remarks / excerpt", "Company"])
    evidence.freeze_panes = "A4"
    evidence.column_dimensions["E"].width = 48
    evidence.column_dimensions["F"].width = 16
    evidence.column_dimensions["G"].width = 80
    evidence.column_dimensions["H"].width = 36

    page_type = store.setting("evidence_page_type", "PDF")
    scorer = store.setting("scorer_name", "")
    for number, ticker, company in roster:
        for year in YEARS:
            project_id = projects.get((company.casefold(), year))
            scores = store.scores(project_id) if project_id is not None else {}
            row = esg.max_row + 1
            prefix = [number, scorer or ticker, company, int(year)]
            esg.append(prefix + [scores[item][0] if item in scores else None for item in ESG_IDS])
            sdg.append(prefix)
            for group, first, last in (("E", "E", "N"), ("S", "O", "X"), ("G", "Y", "AH")):
                col = {"E": "AI", "S": "AJ", "G": "AK"}[group]
                esg[f"{col}{row}"] = f'=IF(COUNT({first}{row}:{last}{row})<10,"",SUM({first}{row}:{last}{row}))'
            esg[f"AL{row}"] = f'=IF(COUNT(E{row}:AH{row})<30,"",SUM(AI{row}:AK{row}))'
            for col, total in (("AM", "AI"), ("AN", "AJ"), ("AO", "AK")):
                esg[f"{col}{row}"] = f'=IF({total}{row}="","",{total}{row}/10/3*100)'
            points = []
            for goal in range(1, 18):
                first_col = 5 + (goal - 1) * 4
                cols = [get_column_letter(first_col + offset) for offset in range(4)]
                for offset, stage in enumerate(STAGES):
                    value = scores.get(f"SDG{goal}-{stage}")
                    sdg.cell(row, first_col + offset, value[0] if value else None)
                a, b, c, p = cols
                sdg[f"{p}{row}"] = f'=IF(COUNT({a}{row}:{c}{row})<3,"",{a}{row}+2*{a}{row}*{b}{row}+3*{a}{row}*{b}{row}*{c}{row})'
                points.append(f"{p}{row}")
            sdg[f"BU{row}"] = f'=IF(COUNT({",".join(f"{get_column_letter(5+(goal-1)*4)}{row}:{get_column_letter(7+(goal-1)*4)}{row}" for goal in range(1,18))})<51,"",SUM({",".join(points)}))'
            sdg[f"BV{row}"] = f'=IF(BU{row}="","",BU{row}/102*100)'
            for item in (*ESG_IDS, *(f"SDG{goal}-{stage}" for goal in range(1, 18) for stage in STAGES)):
                value = scores.get(item)
                if value and value[0] == 1:
                    record = store.score_records(project_id)[item]
                    pins = store.evidence_pins(project_id, item)
                    if pins:
                        for index, pin in enumerate(pins):
                            page = pin["printed_page"] if page_type == "Printed" and pin["printed_page"] else pin["page"]
                            note = f"\nReviewer note: {value[1]}" if index == 0 and value[1] else ""
                            evidence.append([scorer or ticker, int(year), "SDG" if item.startswith("SDG") else "ESG",
                                             item, pin["document"], page, pin["excerpt"] + note, company])
                    else:
                        page = record["printed_pages"] if page_type == "Printed" and record["printed_pages"] else value[3]
                        evidence.append([scorer or ticker, int(year), "SDG" if item.startswith("SDG") else "ESG",
                                         item, value[2], page, value[1], company])

    readme.append(["Verdant export for the consolidated master workbook"])
    for line in (
        "This is a new export. The master workbook has not been modified.",
        "Paste ESG_Scores!A4:AH into the matching master rows. Formula columns AI:AO are included for review.",
        "Paste SDG_Scores!A4:BT into the matching master rows. Formula columns BU:BV are included for review.",
        "Paste Evidence_Log!A4:G into the master evidence log. Column H identifies the company in this export.",
        "Blank score cells mean unreviewed. Zero means reviewed and not found.",
        f"Evidence_Log page references use {page_type} pages (falling back to PDF pages when no printed label was saved).",
        "Known master issue: Ticker values are scorer names, so Evidence_Log COUNTIFS counts scorer-year rather than company-year.",
        "Known master issue: SDG_Scores!D4 and D5 are hardcoded 2021 and 2022 in the supplied workbook.",
        "Known master issue: E/S/G score columns are weighted contributions (up to 33.3), despite the Guide's pillar/10*100 wording.",
    ):
        readme.append([line])
    readme.column_dimensions["A"].width = 120
    return book


def export_master_workbook(store, path, roster_path=None):
    book = build_master_export(store, roster_path)
    book.save(path)
    return Path(path)
