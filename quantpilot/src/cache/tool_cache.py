import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class ToolResultCache:
    def __init__(
        self,
        db_path: str | Path = "data/tool_cache.sqlite3",
        ttl_seconds: int = 3600,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive.")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds

        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tool_results (
                    cache_key TEXT PRIMARY KEY,
                    result_json TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=10)

    @staticmethod
    def _serialize(value: Any) -> str:
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json")

        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    @staticmethod
    def _make_key(
        server: str,
        tool: str,
        arguments: dict[str, Any],
    ) -> str:
        payload = json.dumps(
            {
                "server": server,
                "tool": tool,
                "arguments": arguments,
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(
        self,
        server: str,
        tool: str,
        arguments: dict[str, Any],
    ) -> Any | None:
        key = self._make_key(server, tool, arguments)
        now = time.time()

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT result_json, expires_at
                FROM tool_results
                WHERE cache_key = ?
                """,
                (key,),
            ).fetchone()

            if row is None:
                return None

            result_json, expires_at = row

            if expires_at <= now:
                conn.execute(
                    "DELETE FROM tool_results WHERE cache_key = ?",
                    (key,),
                )
                return None

            return json.loads(result_json)

    def set(
        self,
        server: str,
        tool: str,
        arguments: dict[str, Any],
        result: Any,
    ) -> bool:

        #raise sqlite3.OperationalError("Simulated cache write failure")#just for test 5 of tool result caching
    
        if result is None:
            return False

        try:
            result_json = self._serialize(result)
            key = self._make_key(server, tool, arguments)
        except (TypeError, ValueError):
            return False

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tool_results
                    (cache_key, result_json, expires_at)
                VALUES (?, ?, ?)
                """,
                (
                    key,
                    result_json,
                    time.time() + self.ttl_seconds,
                ),
            )

        return True