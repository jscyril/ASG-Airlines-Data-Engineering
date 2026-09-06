from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor


PATH = Path(__file__).resolve().parents[1] / "ASG_Airlines_Data_Pipeline_Documentation.docx"


def format_run(run):
    run.font.name = "Times New Roman"
    if run._element.rPr is not None:
        run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    run.font.color.rgb = RGBColor(0, 0, 0)


def transparent_bordered_cell(cell):
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:fill"), "clear")

    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = qn("w:" + edge)
        border = borders.find(tag)
        if border is None:
            border = OxmlElement("w:" + edge)
            borders.append(border)
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), "8")  # 1 point
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), "000000")


def main():
    doc = Document(PATH)

    # Set document-wide paragraph styles without changing the existing layout.
    for style in doc.styles:
        if hasattr(style, "font"):
            style.font.name = "Times New Roman"
            style._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
            style._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
            style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
            style.font.color.rgb = RGBColor(0, 0, 0)

    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            format_run(run)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                transparent_bordered_cell(cell)
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        format_run(run)

    for section in doc.sections:
        for part in (section.header, section.footer):
            for paragraph in part.paragraphs:
                for run in paragraph.runs:
                    format_run(run)
            for table in part.tables:
                for row in table.rows:
                    for cell in row.cells:
                        transparent_bordered_cell(cell)
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                format_run(run)

    doc.save(PATH)
    print(PATH)


if __name__ == "__main__":
    main()
