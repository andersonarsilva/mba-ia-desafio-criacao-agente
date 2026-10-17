import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

BUSY_TIMEOUT_MS = 5000


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_MS / 1000)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    try:
        yield connection
    finally:
        connection.close()
