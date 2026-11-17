import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from invoicebot.db import Database
from invoicebot.delivery import DeliveryService


class DeliveryTests(unittest.TestCase):
    def test_failed_delivery_is_retryable_without_duplicate_invoice(self):
        with tempfile.TemporaryDirectory() as td:
            db = Database(Path(td) / "db.sqlite3"); db.initialize()
            with db.connection() as conn:
                conn.execute("INSERT INTO invoices(invoice_number,invoice_year,invoice_type,serial,status,draft_json,delivery_status,created_at) VALUES('26/A/T/001',2026,'T',1,'finalized','{}','ready','now')")
                invoice_id = conn.execute("SELECT id FROM invoices").fetchone()[0]
            client = type("Client", (), {"send_document_file": AsyncMock(side_effect=RuntimeError("temporary"))})()
            result = asyncio.run(DeliveryService(db, client).deliver_pdf(invoice_id, "1555", Path(td) / "x.pdf", "26/A/T/001"))
            self.assertEqual(result["status"], "retry")
            with db.connection() as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT delivery_status FROM invoices").fetchone()[0], "retry")


if __name__ == "__main__": unittest.main()
