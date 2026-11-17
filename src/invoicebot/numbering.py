import sqlite3
from datetime import date

from .db import Database


class InvoiceNumbering:
    def __init__(self, db: Database):
        self.db = db

    def reserve(self, invoice_type: str, on_date: date | None = None) -> tuple[str, int]:
        on_date = on_date or date.today()
        invoice_type = invoice_type.upper()
        if invoice_type not in {"S", "U", "T", "P", "C"}:
            raise ValueError("unsupported invoice type")
        with self.db.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT next_serial FROM invoice_sequences WHERE invoice_year=? AND invoice_type=?", (on_date.year, invoice_type)).fetchone()
            serial = row[0] if row else 1
            if row:
                conn.execute("UPDATE invoice_sequences SET next_serial=? WHERE invoice_year=? AND invoice_type=?", (serial + 1, on_date.year, invoice_type))
            else:
                conn.execute("INSERT INTO invoice_sequences VALUES (?, ?, ?)", (on_date.year, invoice_type, 2))
            number = f"{on_date.year % 100:02d}/A/{invoice_type}/{serial:03d}"
            conn.commit()
            return number, serial

