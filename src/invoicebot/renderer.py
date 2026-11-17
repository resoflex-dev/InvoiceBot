from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from shutil import copy2

from openpyxl import load_workbook

from .template import TemplateMap


MONEY = Decimal("0.01")


@dataclass(frozen=True)
class InvoiceLine:
    description: str
    quantity: Decimal
    unit_price: Decimal

    @property
    def total(self) -> Decimal:
        return (self.quantity * self.unit_price).quantize(MONEY, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class InvoiceDraft:
    invoice_number: str
    customer_name: str
    customer_address: str
    invoice_date: date
    due_date: date
    salesperson: str
    job: str
    payment_terms: str
    lines: tuple[InvoiceLine, ...]
    purchase_reference: str = ""

    @property
    def total(self) -> Decimal:
        return sum((line.total for line in self.lines), Decimal("0.00")).quantize(MONEY)


def render_invoice(template_path: Path, output_xlsx: Path, draft: InvoiceDraft, mapping: TemplateMap = TemplateMap()) -> Decimal:
    workbook = load_workbook(template_path)
    sheet = workbook[mapping.sheet]
    sheet[mapping.customer_name] = draft.customer_name
    sheet[mapping.customer_address] = draft.customer_address
    sheet[mapping.invoice_date] = draft.invoice_date
    sheet[mapping.invoice_number] = draft.invoice_number
    sheet[mapping.purchase_reference] = draft.purchase_reference
    sheet[mapping.salesperson] = draft.salesperson
    sheet[mapping.job] = draft.job
    sheet[mapping.payment_terms] = draft.payment_terms
    sheet[mapping.due_date] = draft.due_date

    for row in range(mapping.line_start, mapping.line_end + 1):
        sheet[f"{mapping.line_qty_col}{row}"] = None
        sheet[f"{mapping.line_description_col}{row}"] = None
        sheet[f"{mapping.line_unit_price_col}{row}"] = None
        sheet[f"{mapping.line_total_col}{row}"] = f"=E{row}*A{row}"
    for row, line in zip(range(mapping.line_start, mapping.line_end + 1), draft.lines):
        sheet[f"{mapping.line_qty_col}{row}"] = float(line.quantity)
        sheet[f"{mapping.line_description_col}{row}"] = line.description
        sheet[f"{mapping.line_unit_price_col}{row}"] = float(line.unit_price)
    sheet[mapping.total_cell] = f"=SUM(F{mapping.line_start}:F{mapping.line_end})"
    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_xlsx)
    return draft.total


def export_pdf_with_excel(xlsx_path: Path, pdf_path: Path) -> None:
    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise RuntimeError("PDF export requires pywin32 and installed Microsoft Excel") from exc
    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    workbook = None
    try:
        workbook = excel.Workbooks.Open(str(xlsx_path.resolve()))
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        workbook.ExportAsFixedFormat(0, str(pdf_path.resolve()))
    finally:
        if workbook is not None:
            workbook.Close(False)
        excel.Quit()

