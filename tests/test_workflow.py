import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from invoicebot.ai import ExtractionService
from invoicebot.config import Settings
from invoicebot.db import Database
from invoicebot.models import InvoiceInput
from invoicebot.service import InvoiceService
from invoicebot.workflow import ConversationWorkflow


class WorkflowTests(unittest.TestCase):
    def test_approval_does_not_assign_number_until_approved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); settings = Settings(database_path=root / "db.sqlite3", template_path=Path("template/Bill-919 - Pack Mart Service Charges.xlsx"), invoice_root=root / "out")
            db = Database(settings.database_path); db.initialize()
            draft = InvoiceInput(invoice_type="T", customer_name="C", customer_address="A", invoice_date=date(2026, 11, 17), due_date=date(2026, 11, 17), salesperson="O", job="J", payment_terms="P", lines=[{"description":"D", "quantity":1, "unit_price":10}])
            class FakeExtractor:
                def extract(self, text): return draft, []
            workflow = ConversationWorkflow(db, FakeExtractor(), InvoiceService(settings, db))
            first = workflow.handle_text("1555", "make invoice")
            self.assertEqual(first["kind"], "approval")
            with db.connection() as conn: self.assertEqual(conn.execute("SELECT COUNT(*) FROM invoice_sequences").fetchone()[0], 0)
            with patch("invoicebot.service.export_pdf_with_excel", side_effect=RuntimeError("no Excel")):
                done = workflow.handle_text("1555", "APPROVE")
            self.assertEqual(done["invoice"]["invoice_number"], "26/A/T/001")


if __name__ == "__main__": unittest.main()
