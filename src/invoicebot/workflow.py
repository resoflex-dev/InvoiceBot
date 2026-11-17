import json
from datetime import datetime, timezone

from .ai import ExtractionService
from .db import Database
from .models import InvoiceInput
from .service import InvoiceService


APPROVE = {"approve", "approved", "yes", "confirm", "confirmed"}
CANCEL = {"cancel", "cancelled", "no", "reject", "rejected"}


class ConversationWorkflow:
    def __init__(self, db: Database, extractor: ExtractionService, invoices: InvoiceService):
        self.db, self.extractor, self.invoices = db, extractor, invoices

    def _save(self, sender_id: str, state: str, draft: InvoiceInput | None):
        now = datetime.now(timezone.utc).isoformat()
        with self.db.connection() as conn:
            conn.execute("INSERT INTO conversations(sender_id,state,draft_json,updated_at) VALUES(?,?,?,?) ON CONFLICT(sender_id) DO UPDATE SET state=excluded.state,draft_json=excluded.draft_json,updated_at=excluded.updated_at", (sender_id, state, draft.model_dump_json() if draft else None, now))

    def handle_text(self, sender_id: str, message: str) -> dict:
        with self.db.connection() as conn:
            row = conn.execute("SELECT state,draft_json FROM conversations WHERE sender_id=?", (sender_id,)).fetchone()
        state = row[0] if row else "idle"
        if state == "awaiting_approval" and row[1]:
            normalized = message.strip().lower()
            if normalized in APPROVE:
                draft = InvoiceInput.model_validate_json(row[1])
                result = self.invoices.finalize(draft, sender_id)
                self._save(sender_id, "idle", None)
                return {"kind": "finalized", "message": f"Invoice {result['invoice_number']} created. Total: {result['total']}", "invoice": result}
            if normalized in CANCEL:
                self._save(sender_id, "idle", None)
                return {"kind": "cancelled", "message": "Draft cancelled. No invoice number was assigned."}
            return {"kind": "approval_required", "message": "Please reply APPROVE or CANCEL."}
        draft, missing = self.extractor.extract(message)
        if missing:
            self._save(sender_id, "awaiting_details", None)
            return {"kind": "clarification", "missing_fields": missing, "message": "Please provide: " + ", ".join(missing)}
        self._save(sender_id, "awaiting_approval", draft)
        total = sum((x.quantity * x.unit_price for x in draft.lines), 0)
        return {"kind": "approval", "message": f"Draft for {draft.customer_name}; total {total}. Reply APPROVE or CANCEL.", "draft": draft.model_dump(mode="json")}

