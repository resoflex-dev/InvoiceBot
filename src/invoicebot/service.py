import json
from datetime import datetime, timezone
from pathlib import Path

from .config import Settings
from .db import Database
from .models import InvoiceInput
from .numbering import InvoiceNumbering
from .renderer import InvoiceDraft, InvoiceLine, export_pdf_with_excel, render_invoice
from .pdf_renderer import render_pdf


class InvoiceService:
    def __init__(self, settings: Settings, db: Database):
        self.settings, self.db = settings, db
        self.numbering = InvoiceNumbering(db)

    def finalize(self, data: InvoiceInput, sender_id: str = "") -> dict:
        invoice_date = data.invoice_date
        number, serial = self.numbering.reserve(data.invoice_type, invoice_date)
        year_dir = self.settings.invoice_root / str(invoice_date.year)
        stem = number.replace("/", "-")
        xlsx_path, pdf_path = year_dir / f"{stem}.xlsx", year_dir / f"{stem}.pdf"
        draft = InvoiceDraft(
            invoice_number=number, customer_name=data.customer_name, customer_address=data.customer_address,
            invoice_date=data.invoice_date, due_date=data.due_date, salesperson=data.salesperson,
            job=data.job, payment_terms=data.payment_terms,
            lines=tuple(InvoiceLine(x.description, x.quantity, x.unit_price) for x in data.lines),
            purchase_reference=data.purchase_reference,
        )
        total = render_invoice(self.settings.template_path, xlsx_path, draft)
        render_pdf(pdf_path, draft)
        pdf_status = "created"
        now = datetime.now(timezone.utc).isoformat()
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO invoices(invoice_number, invoice_year, invoice_type, serial, status, sender_id, draft_json, xlsx_path, pdf_path, delivery_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (number, invoice_date.year, data.invoice_type, serial, "finalized", sender_id, data.model_dump_json(), str(xlsx_path), str(pdf_path) if pdf_path else None, "ready" if pdf_status == "created" else "pdf_pending", now),
            )
            conn.execute("INSERT INTO audit_log(event_type, invoice_number, actor, details_json, created_at) VALUES (?, ?, ?, ?, ?)", ("invoice_finalized", number, sender_id or "system", json.dumps({"total": str(total), "pdf_status": pdf_status}), now))
            invoice_id = conn.execute("SELECT id FROM invoices WHERE invoice_number=?", (number,)).fetchone()[0]
        return {"invoice_id": invoice_id, "invoice_number": number, "total": str(total), "xlsx_path": str(xlsx_path), "pdf_path": str(pdf_path) if pdf_path else None, "pdf_status": pdf_status}

