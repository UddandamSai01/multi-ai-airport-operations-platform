import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "airport_operations.db"


def get_connection(db_path: Path | None = None):
    conn = sqlite3.connect(
        db_path or DB_PATH,
        timeout=10
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn