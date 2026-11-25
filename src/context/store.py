import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken


class ConversationStore:
    """Persistencia SQLite de sesiones y mensajes ya saneados."""

    SCHEMA_VERSION = 2

    def __init__(
        self,
        database_path: str | Path,
        session_timeout_hours: int = 2,
        encryption_key: str | None = None,
        retention_days: int = 30,
    ):
        if session_timeout_hours <= 0:
            raise ValueError("El timeout de sesión debe ser mayor que cero.")
        if retention_days <= 0:
            raise ValueError("La retención debe ser mayor que cero.")
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.session_timeout = timedelta(hours=session_timeout_hours)
        self.retention_days = retention_days
        self._lock = RLock()
        self._cipher = self._build_cipher(encryption_key)
        try:
            self._create_schema()
        except Exception:
            self.connection.close()
            raise

    @staticmethod
    def _build_cipher(key: str | None) -> Fernet | None:
        if not key:
            return None
        try:
            return Fernet(key.encode("ascii"))
        except (ValueError, TypeError) as exc:
            raise ValueError(
                "CONTEXT_ENCRYPTION_KEY no es una clave Fernet válida."
            ) from exc

    def _encrypt(self, value: str) -> str:
        if self._cipher is None:
            return value
        return self._cipher.encrypt(value.encode("utf-8")).decode("ascii")

    def _decrypt(self, value: str) -> str:
        if self._cipher is None:
            return value
        if not value:
            return ""
        try:
            return self._cipher.decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
            raise ValueError(
                "No se pudo descifrar el historial conversacional."
            ) from exc

    def _create_schema(self) -> None:
        with self._lock, self.connection:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_versions (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS storage_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                last_activity_at TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                archived INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL
                    REFERENCES conversation_sessions(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session_time
                ON conversation_messages(session_id, created_at, id);
            CREATE INDEX IF NOT EXISTS idx_sessions_archived_activity
                ON conversation_sessions(archived, last_activity_at);
            """
            )
            self.connection.execute(
                """
                INSERT OR IGNORE INTO schema_versions (version, applied_at)
                VALUES (?, ?)
                """,
                (self.SCHEMA_VERSION, self._now().isoformat()),
            )
            self._ensure_storage_format()
            self._purge_archived()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    def _ensure_storage_format(self) -> None:
        row = self.connection.execute(
            "SELECT value FROM storage_metadata WHERE key = 'content_format'"
        ).fetchone()
        expected = "encrypted" if self._cipher is not None else "plain"
        current = row["value"] if row is not None else "plain"
        if current == "plain" and expected == "encrypted":
            for table, column in (
                ("conversation_sessions", "summary"),
                ("conversation_messages", "content"),
            ):
                rows = self.connection.execute(
                    f"SELECT rowid AS record_id, {column} FROM {table}"
                ).fetchall()
                for item in rows:
                    self.connection.execute(
                        f"UPDATE {table} SET {column} = ? WHERE rowid = ?",
                        (self._encrypt(item[column]), item["record_id"]),
                    )
            self.connection.execute(
                """
                INSERT INTO storage_metadata (key, value)
                VALUES ('content_format', 'encrypted')
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """
            )
        elif row is None:
            self.connection.execute(
                """
                INSERT INTO storage_metadata (key, value) VALUES ('content_format', ?)
                """,
                (expected,),
            )
        elif current != expected:
            raise ValueError(
                "La clave de cifrado no coincide con el formato del historial."
            )

    def get_or_create_session(self) -> tuple[str, str]:
        now = self._now()
        with self._lock:
            row = self.connection.execute(
                """
                SELECT id, summary, last_activity_at
                FROM conversation_sessions
                WHERE archived = 0
                ORDER BY last_activity_at DESC
                LIMIT 1
                """
            ).fetchone()
        if row is not None:
            last_activity = datetime.fromisoformat(row["last_activity_at"])
            if now - last_activity < self.session_timeout:
                return row["id"], self._decrypt(row["summary"])
            with self.connection:
                self.connection.execute(
                    "UPDATE conversation_sessions SET archived = 1 WHERE id = ?",
                    (row["id"],),
                )

        session_id = str(uuid4())
        timestamp = now.isoformat()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO conversation_sessions (id, started_at, last_activity_at)
                VALUES (?, ?, ?)
                """,
                (session_id, timestamp, timestamp),
            )
        return session_id, ""

    def load_recent_messages(
        self, session_id: str, limit: int
    ) -> list[tuple[str, str]]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT role, content FROM conversation_messages
                WHERE session_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return [(row["role"], self._decrypt(row["content"])) for row in reversed(rows)]

    def append_message(self, session_id: str, role: str, content: str) -> None:
        timestamp = self._now().isoformat()
        with self._lock, self.connection:
            self.connection.execute(
                """
                INSERT INTO conversation_messages
                    (session_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, role, self._encrypt(content), timestamp),
            )
            self.connection.execute(
                """
                UPDATE conversation_sessions
                SET last_activity_at = ?
                WHERE id = ?
                """,
                (timestamp, session_id),
            )

    def update_summary(self, session_id: str, summary: str) -> None:
        with self._lock, self.connection:
            self.connection.execute(
                "UPDATE conversation_sessions SET summary = ? WHERE id = ?",
                (self._encrypt(summary), session_id),
            )

    def clear_session(self, session_id: str) -> None:
        with self._lock, self.connection:
            self.connection.execute(
                "DELETE FROM conversation_messages WHERE session_id = ?",
                (session_id,),
            )
            self.connection.execute(
                """
                UPDATE conversation_sessions
                SET summary = '', last_activity_at = ?
                WHERE id = ?
                """,
                (self._now().isoformat(), session_id),
            )

    def _purge_archived(self) -> None:
        cutoff = (self._now() - timedelta(days=self.retention_days)).isoformat()
        # Se eliminan primero los mensajes para que la purga funcione también
        # con bases creadas antes de añadir ON DELETE CASCADE.
        self.connection.execute(
            """
            DELETE FROM conversation_messages
            WHERE session_id IN (
                SELECT id FROM conversation_sessions
                WHERE archived = 1 AND last_activity_at < ?
            )
            """,
            (cutoff,),
        )
        self.connection.execute(
            """
            DELETE FROM conversation_sessions
            WHERE archived = 1 AND last_activity_at < ?
            """,
            (cutoff,),
        )

    def close(self) -> None:
        with self._lock:
            self.connection.execute("PRAGMA wal_checkpoint(PASSIVE)")
            self.connection.close()
