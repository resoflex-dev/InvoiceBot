from dataclasses import dataclass
import httpx
import logging

logger = logging.getLogger("invoicebot.whatsapp")


@dataclass
class WhatsAppClient:
    access_token: str
    phone_number_id: str
    api_version: str = "v27.0"

    async def send_text(self, recipient: str, text: str) -> dict:
        if not self.access_token or not self.phone_number_id:
            raise RuntimeError("WhatsApp credentials are not configured")
        recipient = recipient.lstrip("+")
        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        payload = {"messaging_product": "whatsapp", "to": recipient, "type": "text", "text": {"body": text}}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers={"Authorization": f"Bearer {self.access_token}"}, json=payload)
            if response.is_error:
                logger.error("WhatsApp text API error status=%s body=%s", response.status_code, response.text[:1000])
            response.raise_for_status()
            return response.json()

    async def send_document(self, recipient: str, document_url: str, filename: str, caption: str = "") -> dict:
        if not self.access_token or not self.phone_number_id:
            raise RuntimeError("WhatsApp credentials are not configured")
        recipient = recipient.lstrip("+")
        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        payload = {"messaging_product": "whatsapp", "to": recipient, "type": "document", "document": {"link": document_url, "filename": filename, "caption": caption}}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers={"Authorization": f"Bearer {self.access_token}"}, json=payload)
            response.raise_for_status()
            return response.json()

    async def send_document_file(self, recipient: str, file_path: str, filename: str, caption: str = "") -> dict:
        if not self.access_token or not self.phone_number_id:
            raise RuntimeError("WhatsApp credentials are not configured")
        recipient = recipient.lstrip("+")
        base = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}"
        async with httpx.AsyncClient(timeout=60) as client:
            with open(file_path, "rb") as handle:
                upload = await client.post(f"{base}/media", headers={"Authorization": f"Bearer {self.access_token}"}, data={"messaging_product": "whatsapp", "type": "application/pdf"}, files={"file": (filename, handle, "application/pdf")})
            upload.raise_for_status()
            media_id = upload.json()["id"]
            response = await client.post(f"{base}/messages", headers={"Authorization": f"Bearer {self.access_token}"}, json={"messaging_product": "whatsapp", "to": recipient, "type": "document", "document": {"id": media_id, "filename": filename, "caption": caption}})
            response.raise_for_status()
            return response.json()

