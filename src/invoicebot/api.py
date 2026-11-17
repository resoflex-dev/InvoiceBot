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

    @app.get("/privacy-policy", response_class=HTMLResponse)
    async def privacy_policy():
        return """<!doctype html><html><head><meta charset='utf-8'><title>Resoflex InvoiceBot Privacy Policy</title></head><body><h1>Resoflex InvoiceBot Privacy Policy</h1><p><strong>Effective date:</strong> 17 November 2026</p><p>Resoflex InvoiceBot is operated by Resoflex IT Solutions (Pvt) Ltd. This policy explains how the service handles information sent through WhatsApp.</p><h2>Information we process</h2><ul><li>WhatsApp sender identifier and message content sent to the service.</li><li>Customer, invoice, line-item, date, and payment-term details supplied for invoice preparation.</li><li>Technical webhook event identifiers, timestamps, delivery status, and audit records.</li></ul><h2>How we use information</h2><p>We use this information to answer invoice requests, ask clarification questions, prepare approved invoices, generate PDF documents, deliver approved documents through WhatsApp, prevent duplicate webhook processing, maintain audit records, and protect the service.</p><h2>AI processing</h2><p>When configured, message text may be sent to the OpenAI API to extract structured invoice details. The service is instructed not to invent prices, customer data, tax rates, or payment details. Users should not send unnecessary sensitive information.</p><h2>Storage and retention</h2><p>Invoice and audit data is stored on the operator's secured server. Generated invoice files are stored for operational and accounting purposes for the period required by the operator's business and legal obligations.</p><h2>Sharing</h2><p>Information is shared only with service providers required to operate the requested workflow, such as Meta WhatsApp Cloud API and, when enabled, OpenAI for extraction. We do not sell personal information.</p><h2>Security</h2><p>The service uses HTTPS, access controls, webhook signature validation, approved-sender restrictions, idempotency, and protected server configuration. No internet service can guarantee absolute security.</p><h2>Your requests</h2><p>To request access, correction, or deletion of information associated with your WhatsApp number, contact the Resoflex administrator through the business contact channel that provided this service and include your number in international format. Deletion instructions are available at <a href='/data-deletion'>/data-deletion</a>.</p><h2>Changes</h2><p>This policy may be updated when the service or its data handling changes. The effective date above will be updated when material changes are made.</p></body></html>"""

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
                    if sender and text and (settings.environment != "production" or sender in settings.approved_sender_ids):
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

