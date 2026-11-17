import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS webhook_events (event_id TEXT PRIMARY KEY, received_at TEXT NOT NULL, payload_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS conversations (sender_id TEXT PRIMARY KEY, state TEXT NOT NULL, draft_json TEXT, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS invoice_sequences (invoice_year INTEGER NOT NULL, invoice_type TEXT NOT NULL, next_serial INTEGER NOT NULL, PRIMARY KEY(invoice_year, invoice_type));
CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_number TEXT UNIQUE NOT NULL, invoice_year INTEGER NOT NULL, invoice_type TEXT NOT NULL, serial INTEGER NOT NULL, status TEXT NOT NULL, sender_id TEXT, draft_json TEXT NOT NULL, xlsx_path TEXT, pdf_path TEXT, delivery_status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL, cancelled_at TEXT);
CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, invoice_number TEXT, actor TEXT, details_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS delivery_attempts (id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id INTEGER NOT NULL, recipient TEXT NOT NULL, status TEXT NOT NULL, attempt_count INTEGER NOT NULL DEFAULT 0, last_error TEXT, next_attempt_at TEXT, created_at TEXT NOT NULL, UNIQUE(invoice_id, recipient));
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def initialize(self):
        with self.connection() as conn:
            conn.executescript(SCHEMA)

    def record_webhook(self, event_id: str, payload: dict, received_at: str) -> bool:
        with self.connection() as conn:
            try:
                conn.execute("INSERT INTO webhook_events VALUES (?, ?, ?)", (event_id, received_at, json.dumps(payload)))
                return True
            except sqlite3.IntegrityError:
                return False

