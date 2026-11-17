"""Fill a copy of the workbook template while preserving unsupported Excel features."""
import html
import re
from pathlib import Path
from zipfile import ZipFile

from verdant.config import PROJECT_ROOT, RESOURCES_DIR
from verdant.services.master_export import build_master_export

TEMPLATE_PATH = RESOURCES_DIR / "ESG_SDG_Scoring_Consolidated_Template.xlsx"
BENCHMARK_PATH = PROJECT_ROOT.parent / "ESG_SDG_Scoring_Consolidated - Template File.xlsx"
ROW_RE = re.compile(rb'(<row\b[^>]*\br="(\d+)"[^>]*>)(.*?)(</row>)', re.S)
CELL_RE = re.compile(rb'<c\b[^>]*\br="([A-Z]+\d+)"[^>]*(?:/>|>.*?</c>)', re.S)
STYLE_RE = re.compile(rb'\bs="(\d+)"')


def _cell_xml(reference, value, previous=b""):
    style = STYLE_RE.search(previous.split(b">", 1)[0])
    attributes = f' r="{reference}"' + (f' s="{style.group(1).decode()}"' if style else "")
    if value is None:
        return f"<c{attributes}/>".encode()
    if isinstance(value, str) and value.startswith("="):
        return f"<c{attributes}><f>{html.escape(value[1:], quote=False)}</f></c>".encode()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"<c{attributes}><v>{value}</v></c>".encode()
    escaped = html.escape(str(value), quote=False)
    return f'<c{attributes} t="inlineStr"><is><t>{escaped}</t></is></c>'.encode("utf-8")


def _patch_sheet(xml, replacements):
    found_rows = set()

    def patch_row(match):
        row_number = int(match.group(2))
        changes = replacements.get(row_number)
        if not changes:
            return match.group(0)
        found_rows.add(row_number)
        seen = set()

        def patch_cell(cell_match):
            reference = cell_match.group(1).decode()
            if reference not in changes:
                return cell_match.group(0)
            seen.add(reference)
            return _cell_xml(reference, changes[reference], cell_match.group(0))

        body = CELL_RE.sub(patch_cell, match.group(3))
        # Template rows are preformatted; this handles a cell with no style node.
        missing = b"".join(_cell_xml(ref, value) for ref, value in changes.items() if ref not in seen)
        return match.group(1) + body + missing + match.group(4)

    patched = ROW_RE.sub(patch_row, xml)
    absent = set(replacements) - found_rows
    if absent:
        raise ValueError(f"The template is missing data rows: {sorted(absent)[:5]}")
    return patched


def _sheet_values(sheet, last_col):
    return {row[0].row: {cell.coordinate: cell.value for cell in row}
            for row in sheet.iter_rows(min_row=4, max_col=last_col)}


def export_general_workbook(store, destination, template_path=None):
    source = Path(template_path or TEMPLATE_PATH).resolve()
    destination = Path(destination).resolve()
    if source == destination or destination == BENCHMARK_PATH.resolve():
        raise ValueError("Choose a new output file; the template cannot be overwritten.")
    if not source.is_file():
        raise FileNotFoundError(f"Consolidated template missing: {source}")
    generated = build_master_export(store, roster_path=source)
    replacements = {
        "xl/worksheets/sheet4.xml": _sheet_values(generated["ESG_Scores"], 41),
        "xl/worksheets/sheet5.xml": _sheet_values(generated["SDG_Scores"], 74),
        "xl/worksheets/sheet7.xml": _sheet_values(generated["Evidence_Log"], 8),
    }
    scorer = store.setting("scorer_name", "")
    if scorer:
        for row in replacements["xl/worksheets/sheet4.xml"]:
            replacements["xl/worksheets/sheet4.xml"][row][f"AS{row}"] = scorer
        for row in replacements["xl/worksheets/sheet5.xml"]:
            replacements["xl/worksheets/sheet5.xml"][row][f"BZ{row}"] = scorer
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(source) as source_zip, ZipFile(destination, "w") as output_zip:
        for member in source_zip.infolist():
            content = source_zip.read(member.filename)
            if member.filename in replacements:
                content = _patch_sheet(content, replacements[member.filename])
            elif member.filename == "xl/workbook.xml":
                content = re.sub(rb'<calcPr\b([^>]*)/?>',
                    lambda m: b'<calcPr' + re.sub(rb'\s+(?:fullCalcOnLoad|forceFullCalc)="[^"]*"', b'', m.group(1).rstrip(b'/'))
                    + b' fullCalcOnLoad="1" forceFullCalc="1"/>', content, count=1)
            output_zip.writestr(member, content)
    return destination
