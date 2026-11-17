from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook


@dataclass(frozen=True)
class TemplateMap:
    sheet: str = "Service Invoice"
    customer_name: str = "B7"
    customer_address: str = "B8"
    invoice_date: str = "F7"
    invoice_number: str = "F8"
    purchase_reference: str = "F9"
    salesperson: str = "A13"
    job: str = "C13"
    payment_terms: str = "D13"
    due_date: str = "F13"
    line_start: int = 16
    line_end: int = 30
    line_qty_col: str = "A"
    line_description_col: str = "B"
    line_unit_price_col: str = "E"
    line_total_col: str = "F"
    total_cell: str = "F31"


def inspect_template(path: Path) -> dict:
    workbook = load_workbook(path, data_only=False)
    result = {"sheets": []}
    for ws in workbook.worksheets:
        cells = {}
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None:
                    cells[cell.coordinate] = {"value": cell.value, "data_type": cell.data_type}
        result["sheets"].append(
            {
                "title": ws.title,
                "dimension": ws.calculate_dimension(),
                "print_area": str(ws.print_area) if ws.print_area else None,
                "merged_ranges": sorted(str(r) for r in ws.merged_cells.ranges),
                "cells": cells,
            }
        )
    return result

