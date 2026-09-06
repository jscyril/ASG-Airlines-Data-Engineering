from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "solution_walkthrough.docx"


def set_run_font(run, size=10.5, bold=False, italic=False):
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor(0, 0, 0)
    run.bold = bold
    run.italic = italic


def clear_cell_shading(cell):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), "clear")
    shd.set(qn("w:val"), "clear")


def set_cell_borders(cell):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + edge
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "8")  # 1 pt, approximately 1 px
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "000000")


def style_table(table):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for row in table.rows:
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            clear_cell_shading(cell)
            set_cell_borders(cell)
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    set_run_font(run, 9.5)


def add_table(doc, headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    for i, header in enumerate(headers):
        table.rows[0].cells[i].text = header
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = str(value)
    style_table(table)
    doc.add_paragraph()
    return table


def add_heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        set_run_font(run, {1: 16, 2: 13, 3: 11}[level], bold=True)
    return p


def add_body(doc, text, bold_prefix=None):
    p = doc.add_paragraph()
    if bold_prefix and text.startswith(bold_prefix):
        r = p.add_run(bold_prefix)
        set_run_font(r, bold=True)
        r = p.add_run(text[len(bold_prefix):])
        set_run_font(r)
    else:
        r = p.add_run(text)
        set_run_font(r)
    p.paragraph_format.space_after = Pt(5)
    return p


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        r = p.add_run(item)
        set_run_font(r)


def main():
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    styles = doc.styles
    for style_name in ["Normal", "Body Text", "List Bullet", "List Number"]:
        style = styles[style_name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style.font.size = Pt(10.5)
        style.font.color.rgb = RGBColor(0, 0, 0)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run("ASG Airlines\nEnd-to-End Data Engineering Case Study")
    set_run_font(r, 18, bold=True)
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sub.add_run("Solution walkthrough and delivery documentation")
    set_run_font(r, 11, italic=True)
    doc.add_paragraph()

    add_heading(doc, "1. Objective", 1)
    add_body(doc, "Turn inconsistent airline operational workbook data into trustworthy flight, booking, payment, and KPI data for Power BI while preserving audit evidence and preventing passenger PII from reaching serving tables.")

    add_heading(doc, "2. Architecture and data flow", 1)
    add_body(doc, "The production target uses ADLS Gen2, Data Factory, Databricks/Delta, Key Vault, Entra ID, Azure Monitor, and Power BI. This submission provides an equivalent local pandas implementation for reproducibility without an Azure subscription.")
    add_table(doc, ["Layer", "Purpose", "Output"], [
        ("Raw/Bronze", "Restricted immutable source evidence", "Original workbook and ingestion metadata"),
        ("Curated/Silver", "Normalize, validate, recalculate, and protect PII", "Safe flights, bookings, payments, passengers_safe"),
        ("Quarantine", "Preserve rejected records with reason codes", "Reason-coded invalid/suspicious rows"),
        ("Gold", "Analytics-ready facts, dimensions, and aggregates", "Power BI serving tables"),
    ])
    add_body(doc, "Data flow: source workbook → profile → normalize and validate → curated safe data plus quarantine → Gold facts/dimensions/KPIs → Power BI semantic model.")

    add_heading(doc, "3. Data model and grain", 1)
    add_table(doc, ["Table", "Grain", "Key analytical fields"], [
        ("fact_flight_operations", "One valid flight operation", "flight_id, airline, route, duration_minutes, overnight_flag"),
        ("fact_bookings", "One valid booking", "booking_id, passenger_key_hash, flight_id, status"),
        ("fact_payments", "One payment row with a valid booking reference", "payment_id, booking_id, amount"),
        ("dim_flight", "One row per flight_id for relationship integrity", "flight_id, airline, route"),
        ("dim_airline / dim_route / dim_date", "One row per dimension member", "airline, route, departure_date"),
    ])
    add_body(doc, "Power BI relationships are single-direction: dim_airline → dim_flight; dim_route → dim_flight; dim_flight → both fact_flight_operations and fact_bookings; fact_bookings → fact_payments. No fact-to-fact or bidirectional relationships are used.")

    add_heading(doc, "4. Source profile and current results", 1)
    add_table(doc, ["Metric", "Result"], [
        ("Flights / bookings / payments / passengers", "1,020 / 1,000 / 1,000 / 1,039"),
        ("Malformed flight IDs", "273"),
        ("Missing airline values", "41"),
        ("Missing payment amounts", "78"),
        ("Missing booking statuses", "45"),
        ("Source overnight flights / transformed flags", "124 / 125"),
        ("Duplicate source flight rows", "15 exact duplicate rows"),
    ])

    add_heading(doc, "5. Transformation and data-quality rules", 1)
    add_bullets(doc, [
        "Normalize column names, trim text, and convert blank strings to nulls.",
        "Validate flight IDs against ^[A-Z]{2}[0-9]{3}; never guess a replacement for malformed IDs.",
        "Parse timestamps and add one day when arrival precedes departure, then calculate duration_minutes from adjusted timestamps.",
        "Flag null, non-positive, or over-24-hour durations; retain rejected records in quarantine.",
        "Accept only CONFIRMED, CANCELLED, and PENDING booking statuses; preserve cancelled bookings for analysis.",
        "Keep missing payment amounts null and exclude them from payment totals.",
        "Write quality results with dataset, rule, and failed-record counts.",
    ])

    add_heading(doc, "6. PII protection", 1)
    add_body(doc, "Raw passenger fields are restricted to raw storage. passengers_safe contains only passenger_key_hash, age_band, and gender. Curated and Gold bookings use passenger_key_hash and remove passenger_id, passport_number, emergency-contact fields, email, phone, Aadhaar, and names. Power BI receives only Gold and quality outputs.")
    add_body(doc, "The local test suite includes a regression test that fails if raw booking PII reappears in the curated output.")

    add_heading(doc, "7. KPI definitions and reconciled values", 1)
    add_table(doc, ["KPI", "Definition", "Value"], [
        ("Total flights", "Valid Gold flight-operation rows", "747"),
        ("Average duration", "Mean recalculated duration_minutes", "164.1 minutes"),
        ("Median duration", "Median recalculated duration_minutes", "164 minutes"),
        ("Valid bookings", "Allowed status and valid flight reference", "679"),
        ("Cancellation rate", "Cancelled valid bookings / all valid bookings", "33.7%"),
        ("Payment total", "Sum of non-null amounts for valid booking references", "5,419,385.34"),
    ])

    add_heading(doc, "8. Power BI report", 1)
    add_body(doc, "The report contains five pages: Executive Overview, Duration Analysis, Route Performance, Airline Trends, and Data Quality & Anomalies. Slicers use dimensions and all visuals exclude passenger PII. After the safe-schema change, the PBIX must be refreshed and stale PII fields removed before delivery.")
    add_bullets(doc, [
        "Executive Overview: six KPI cards, airline and route traffic, and operational slicers.",
        "Duration Analysis: duration distribution, airline/route averages, same-day versus overnight, and flight detail.",
        "Route Performance: route traffic, duration, source/destination matrix, booking volume, and slicers.",
        "Airline Trends: flight volume, duration, booking status, cancellation rate, and payment totals.",
        "Data Quality & Anomalies: quality cards, failures by rule, missing fields, quarantine counts, and detail tables.",
    ])

    add_heading(doc, "9. Testing and reproducibility", 1)
    add_body(doc, "Run the project with Python 3.11 and uv: uv sync; uv run pytest; uv run python src/profile.py; uv run python src/transform.py; uv run python src/gold.py. The current automated suite passes 4 tests, including overnight adjustment, PII-safe passenger output, PII-safe booking output, and Gold KPI reconciliation.")

    add_heading(doc, "10. Security, deployment, and limitations", 1)
    add_bullets(doc, [
        "Use managed identities, Key Vault, Entra ID groups, layer-specific ADLS permissions, and Azure Monitor in production.",
        "Keep raw workbooks and PBIX files outside source control; .gitignore excludes raw workbooks, generated local data, and PBIX artifacts.",
        "The current implementation is local batch pandas, not a deployed Azure pipeline. Production next steps are ADF orchestration, run metadata/checksums, CI/CD, monitoring, and scheduled Power BI refresh.",
    ])

    add_heading(doc, "11. Submission checklist", 1)
    add_table(doc, ["Deliverable", "Status / action"], [
        ("Working pipeline and tests", "Complete; 4 tests pass"),
        ("Cleaned and Gold datasets", "Complete; regenerated after PII fix"),
        ("Power BI report and screenshots", "Complete locally; refresh PBIX after safe-schema change"),
        ("README and walkthrough", "Complete in Markdown and this Word document"),
        ("Original workbook / raw PII", "Keep restricted; exclude from submission archive"),
        ("Final package", "Rebuild ZIP only after refreshed PBIX is saved"),
    ])

    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            if run.font.name != "Times New Roman":
                set_run_font(run)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
