import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from invoicebot.config import Settings
from invoicebot.db import Database
from invoicebot.models import InvoiceInput
from invoicebot.service import InvoiceService


class ServiceTests(unittest.TestCase):
    def test_finalize_assigns_number_only_at_finalize_and_records_invoice(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            settings = Settings(database_path=root / "db.sqlite3", template_path=Path("template/Bill-919 - Pack Mart Service Charges.xlsx"), invoice_root=root / "Invoices")
            db = Database(settings.database_path); db.initialize()
            invoice = InvoiceInput(invoice_type="T", customer_name="Customer", customer_address="Address", invoice_date=date(2026, 11, 17), due_date=date(2026, 11, 17), salesperson="Office", job="Support", payment_terms="Deposit", lines=[{"description":"Work", "quantity":"1", "unit_price":"100.00"}])
            result = InvoiceService(settings, db).finalize(invoice, "local")
            self.assertEqual(result["invoice_number"], "26/A/T/001")
            with db.connection() as conn:
                row = conn.execute("SELECT invoice_number, status FROM invoices").fetchone()
            self.assertEqual(tuple(row), ("26/A/T/001", "finalized"))
            self.assertTrue(Path(result["pdf_path"]).exists())


if __name__ == "__main__":
    unittest.main()
