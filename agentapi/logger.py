"""Request/response logging backed by SQLite."""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentapi.models import RequestLog

_SCHEMA = """
CREATE TABLE IF NOT EXISTS request_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    method      TEXT    NOT NULL,
    path        TEXT    NOT NULL,
    status_code INTEGER NOT NULL,
    client_ip   TEXT    NOT NULL DEFAULT '',
    request_body  TEXT DEFAULT '',
    response_body TEXT DEFAULT '',
    duration_ms REAL    DEFAULT 0.0,
    api_key_prefix TEXT DEFAULT ''
);
"""


class RequestLogger:
    """Writes request logs to a SQLite database."""

    def __init__(self, db_path: str = "agentapi.db") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def log(
        self,
        method: str,
        path: str,
        status_code: int,
        client_ip: str = "",
        request_body: Any = None,
        response_body: Any = None,
        duration_ms: float = 0.0,
        api_key_prefix: str = "",
    ) -> None:
        """Insert a request log entry."""
        ts = datetime.now(timezone.utc).isoformat()
        req_str = json.dumps(request_body) if request_body is not None else ""
        resp_str = json.dumps(response_body) if response_body is not None else ""
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO request_logs
                   (timestamp, method, path, status_code, client_ip,
                    request_body, response_body, duration_ms, api_key_prefix)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ts, method, path, status_code, client_ip,
                 req_str, resp_str, duration_ms, api_key_prefix[:12] if api_key_prefix else ""),
            )

    def get_recent(self, limit: int = 50) -> list[RequestLog]:
        """Return the most recent log entries."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM request_logs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [RequestLog(**dict(r)) for r in rows]
