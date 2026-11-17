import json
from typing import Any

from .models import InvoiceInput


SYSTEM_PROMPT = """Extract invoice details from the user's message as JSON matching the InvoiceInput schema. Never invent prices, customer data, tax rates, payment details, or missing values. Return only JSON. If required data is missing, return {\"missing_fields\":[...]} instead."""


class ExtractionService:
    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    def extract(self, message: str) -> tuple[InvoiceInput | None, list[str]]:
        if not self.api_key:
            return None, ["AI extraction is not configured; provide structured invoice data or set OPENAI_API_KEY"]
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(model=self.model, temperature=0, response_format={"type": "json_object"}, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": message}])
        data: dict[str, Any] = json.loads(response.choices[0].message.content)
        if data.get("missing_fields"):
            return None, list(data["missing_fields"])
        return InvoiceInput.model_validate(data), []

