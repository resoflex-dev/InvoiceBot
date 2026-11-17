import json
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from .config import Settings
from .db import Database
from .security import valid_signature
from .models import InvoiceInput
from .service import InvoiceService
from .ai import ExtractionService
from .workflow import ConversationWorkflow
from .whatsapp import WhatsAppClient
from .delivery import DeliveryService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    db = Database(settings.database_path)
    db.initialize()
    app = FastAPI(title="Resoflex InvoiceBot", version="1.0.0")
    app.state.settings, app.state.db = settings, db
    app.state.service = InvoiceService(settings, db)
    app.state.workflow = ConversationWorkflow(db, ExtractionService(settings.openai_api_key, settings.openai_model), app.state.service)
    app.state.whatsapp = WhatsAppClient(settings.whatsapp_access_token, settings.whatsapp_phone_number_id)
    app.state.delivery = DeliveryService(db, app.state.whatsapp)

    @app.get("/health")
    async def health():
        return {"status": "ok", "environment": settings.environment}

    @app.get("/data-deletion", response_class=HTMLResponse)
    async def data_deletion_instructions():
        return """<!doctype html><html><head><meta charset='utf-8'><title>Resoflex InvoiceBot data deletion</title></head><body><h1>Resoflex InvoiceBot data deletion</h1><p>To request deletion of data held by Resoflex InvoiceBot, contact the Resoflex administrator through the business contact channel that provided this service and include your WhatsApp number in international format.</p><p>We will verify the request, delete conversation records, invoice drafts, webhook records, audit records, and generated invoice files associated with the requester where legally permitted, and confirm completion.</p><p>This page is provided for Meta platform data-deletion instructions.</p></body></html>"""

    @app.get("/webhook")
    async def verify_webhook(hub_mode: str | None = Query(default=None, alias="hub.mode"), hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"), hub_challenge: str | None = Query(default=None, alias="hub.challenge")):
        if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
            return int(hub_challenge or "0") if (hub_challenge or "").isdigit() else (hub_challenge or "")
        raise HTTPException(status_code=403, detail="verification failed")

    @app.post("/webhook")
    async def receive_webhook(request: Request, x_hub_signature_256: str | None = Header(default=None)):
        raw = await request.body()
        if settings.whatsapp_app_secret and not valid_signature(raw, x_hub_signature_256 or "", settings.whatsapp_app_secret):
            raise HTTPException(status_code=401, detail="invalid signature")
        payload = json.loads(raw or b"{}")
        event_id = request.headers.get("x-event-id") or payload.get("event_id") or str(hash(raw))
        if not db.record_webhook(event_id, payload, datetime.now(timezone.utc).isoformat()):
            return {"status": "duplicate"}
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for message in value.get("messages", []):
                    sender = message.get("from")
                    text = (message.get("text") or {}).get("body")
                    if sender and text and (not settings.approved_sender_ids or sender in settings.approved_sender_ids):
                        result = app.state.workflow.handle_text(sender, text)
                        if settings.whatsapp_access_token and settings.whatsapp_phone_number_id:
                            await app.state.whatsapp.send_text(sender, result["message"])
        return {"status": "accepted"}

    @app.post("/invoices/finalize")
    async def finalize_invoice(invoice: InvoiceInput, x_sender_id: str | None = Header(default="local-test")):
        if settings.environment == "production" and x_sender_id not in settings.approved_sender_ids:
            raise HTTPException(status_code=403, detail="sender is not authorized")
        return app.state.service.finalize(invoice, x_sender_id or "")

    @app.post("/invoices/{invoice_id}/deliver")
    async def deliver_invoice(invoice_id: int, recipient: str, x_sender_id: str | None = Header(default="local-test")):
        if settings.environment == "production" and x_sender_id not in settings.approved_sender_ids:
            raise HTTPException(status_code=403, detail="sender is not authorized")
        with db.connection() as conn:
            row = conn.execute("SELECT invoice_number,pdf_path FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        if not row or not row[1]:
            raise HTTPException(status_code=404, detail="invoice PDF is not available")
        return await app.state.delivery.deliver_pdf(invoice_id, recipient, __import__('pathlib').Path(row[1]), row[0])

    return app


app = create_app()

