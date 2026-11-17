import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .db import Database
from .whatsapp import WhatsAppClient


class DeliveryService:
    def __init__(self, db: Database, client: WhatsAppClient, max_attempts: int = 5):
        self.db, self.client, self.max_attempts = db, client, max_attempts

    async def deliver_pdf(self, invoice_id: int, recipient: str, pdf_path: Path, invoice_number: str) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        with self.db.connection() as conn:
            conn.execute("INSERT INTO delivery_attempts(invoice_id,recipient,status,created_at) VALUES(?,?,?,?) ON CONFLICT(invoice_id,recipient) DO NOTHING", (invoice_id, recipient, "pending", now))
            row = conn.execute("SELECT attempt_count FROM delivery_attempts WHERE invoice_id=? AND recipient=?", (invoice_id, recipient)).fetchone()
            attempts = int(row[0])
        if attempts >= self.max_attempts:
            return {"status": "dead_letter", "attempts": attempts}
        try:
            result = await self.client.send_document_file(recipient, str(pdf_path), f"{invoice_number.replace('/', '-')}.pdf", f"Invoice {invoice_number}")
            with self.db.connection() as conn:
                conn.execute("UPDATE delivery_attempts SET status='sent', attempt_count=attempt_count+1, last_error=NULL WHERE invoice_id=? AND recipient=?", (invoice_id, recipient))
                conn.execute("UPDATE invoices SET delivery_status='sent' WHERE id=?", (invoice_id,))
            return {"status": "sent", "response": result}
        except Exception as exc:
            delay = 2 ** attempts
            next_at = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()
            with self.db.connection() as conn:
                conn.execute("UPDATE delivery_attempts SET status='retry', attempt_count=attempt_count+1, last_error=?, next_attempt_at=? WHERE invoice_id=? AND recipient=?", (str(exc), next_at, invoice_id, recipient))
                conn.execute("UPDATE invoices SET delivery_status='retry' WHERE id=?", (invoice_id,))
            return {"status": "retry", "attempts": attempts + 1, "next_attempt_at": next_at}

