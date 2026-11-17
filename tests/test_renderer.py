import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from openpyxl import load_workbook

from invoicebot.renderer import InvoiceDraft, InvoiceLine, render_invoice
from invoicebot.template import inspect_template


ROOT = Path(__file__).parents[1]
TEMPLATE = ROOT / "template" / "Bill-919 - Pack Mart Service Charges.xlsx"


class RendererTests(unittest.TestCase):
    def test_inspection_captures_exact_template_structure(self):
        report = inspect_template(TEMPLATE)
        service = report["sheets"][0]
        self.assertEqual(service["title"], "Service Invoice")
        self.assertEqual(service["dimension"], "A1:I41")
        self.assertIn("A11:F11", service["merged_ranges"])
        self.assertEqual(service["cells"]["F16"]["value"], "=E16*A16")
        self.assertEqual(service["cells"]["F31"]["value"], "=SUM(F16:F30)")

    def test_render_preserves_layout_and_writes_sample(self):
        draft = InvoiceDraft(
            invoice_number="26/A/T/001",
            customer_name="Sample Customer",
            customer_address="Sample Address",
            invoice_date=date(2026, 11, 16),
            due_date=date(2026, 11, 16),
            salesperson="Office",
            job="Remote Support",
            payment_terms="Bank Deposit / Cheque",
            lines=(InvoiceLine("Support", Decimal("2"), Decimal("1250.25")),),
        )
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "sample.xlsx"
            total = render_invoice(TEMPLATE, output, draft)
            self.assertEqual(total, Decimal("2500.50"))
            wb = load_workbook(output, data_only=False)
            ws = wb["Service Invoice"]
            self.assertEqual(ws["F8"].value, "26/A/T/001")
            self.assertEqual(ws["B16"].value, "Support")
            self.assertEqual(ws["F31"].value, "=SUM(F16:F30)")
            self.assertEqual(str(ws.print_area), "'Service Invoice'!$A$1:$F$37")


if __name__ == "__main__":
    unittest.main()

