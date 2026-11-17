import tempfile
import unittest
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from invoicebot.api import create_app
from invoicebot.config import Settings
from invoicebot.db import Database
from invoicebot.numbering import InvoiceNumbering
from invoicebot.security import valid_signature


class V1Tests(unittest.TestCase):
    def test_numbering_is_independent_by_type_and_year(self):
        with tempfile.TemporaryDirectory() as td:
            db = Database(Path(td) / "x.sqlite3"); db.initialize(); n = InvoiceNumbering(db)
            self.assertEqual(n.reserve("T", date(2026, 1, 1))[0], "26/A/T/001")
            self.assertEqual(n.reserve("T", date(2026, 1, 1))[0], "26/A/T/002")
            self.assertEqual(n.reserve("P", date(2026, 1, 1))[0], "26/A/P/001")
            self.assertEqual(n.reserve("T", date(2027, 1, 1))[0], "27/A/T/001")

    def test_signature_and_webhook_idempotency(self):
        with tempfile.TemporaryDirectory() as td:
            settings = Settings(database_path=Path(td) / "x.sqlite3", whatsapp_verify_token="token", whatsapp_app_secret="secret")
            client = TestClient(create_app(settings))
            self.assertEqual(client.get("/health").status_code, 200)
            body = b'{"event_id":"abc"}'
            import hmac, hashlib
            sig = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
            self.assertTrue(valid_signature(body, sig, "secret"))
            self.assertEqual(client.post("/webhook", content=body, headers={"x-hub-signature-256": sig}).json(), {"status": "accepted"})
            self.assertEqual(client.post("/webhook", content=body, headers={"x-hub-signature-256": sig}).json(), {"status": "duplicate"})

    def test_production_webhook_requires_approved_sender(self):
        with tempfile.TemporaryDirectory() as td:
            settings = Settings(database_path=Path(td) / "x.sqlite3", whatsapp_verify_token="token", whatsapp_app_secret="secret", environment="production", approved_sender_ids_raw="94770000000")
            client = TestClient(create_app(settings))
            payload = {"entry": [{"changes": [{"value": {"messages": [{"from": "94771111111", "text": {"body": "test"}}]}}]}]}
            import hmac, hashlib, json
            body = json.dumps(payload).encode()
            sig = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
            self.assertEqual(client.post("/webhook", content=body, headers={"x-hub-signature-256": sig}).json(), {"status": "accepted"})
            with client.app.state.db.connection() as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0], 0)

    def test_admin_logs_require_token(self):
        with tempfile.TemporaryDirectory() as td:
            settings = Settings(database_path=Path(td) / "x.sqlite3", admin_log_token="secret-log-token")
            client = TestClient(create_app(settings))
            self.assertEqual(client.get("/admin/logs").status_code, 401)
            self.assertEqual(client.get("/admin/logs", headers={"x-admin-log-token": "secret-log-token"}).status_code, 200)


if __name__ == "__main__":
    unittest.main()

