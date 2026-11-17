import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("APP_ENV", "development")
    database_path: Path = Path(os.getenv("DATABASE_PATH", "var/invoicebot.sqlite3"))
    template_path: Path = Path(os.getenv("TEMPLATE_PATH", "template/Bill-919 - Pack Mart Service Charges.xlsx"))
    invoice_root: Path = Path(os.getenv("INVOICE_ROOT", "D:/Resoflex/Invoices"))
    whatsapp_verify_token: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    whatsapp_app_secret: str = os.getenv("WHATSAPP_APP_SECRET", "")
    whatsapp_access_token: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    whatsapp_phone_number_id: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    approved_sender_ids_raw: str = os.getenv("APPROVED_SENDER_IDS", "")

    @property
    def approved_sender_ids(self) -> frozenset[str]:
        return frozenset(x.strip() for x in self.approved_sender_ids_raw.split(",") if x.strip())

