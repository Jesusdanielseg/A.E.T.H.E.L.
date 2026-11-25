import sqlite3

import pytest
from cryptography.fernet import Fernet

from src.context.manager import ContextManager
from src.context.sanitizer import sanitize_text
from src.core.llm import RespuestaLLM


def test_sanitizer_removes_secrets_email_and_home_path() -> None:
    clean = sanitize_text(
        "key=AIzaSecret_123 email=ana@example.com "
        "path=/home/daniel/private.txt password=hidden"
    )

    assert "AIzaSecret" not in clean
    assert "ana@example.com" not in clean
    assert "/home/daniel" not in clean
    assert "hidden" not in clean


def test_sanitizer_masks_token_api_key_and_aq_assignments() -> None:
    clean = sanitize_text("token: abc123 api_key=secret AQ.private_value")

    assert "abc123" not in clean
    assert "secret" not in clean
    assert "AQ.private_value" not in clean


def test_context_persists_sanitized_turns_and_reloads_recent_messages(tmp_path) -> None:
    database = tmp_path / "memory.db"
    context = ContextManager(database, "Eres A.E.T.H.E.L.", max_messages=14)
    context.add_message("user", "Mi correo es ana@example.com")
    context.add_message("assistant", "Entendido")
    session_id = context.session_id
    context.close()

    reloaded = ContextManager(database, "Eres A.E.T.H.E.L.", max_messages=14)

    assert reloaded.session_id == session_id
    assert reloaded.messages[0].content == "Mi correo es [CORREO_OCULTO]"
    with sqlite3.connect(database) as connection:
        stored = connection.execute(
            "SELECT content FROM conversation_messages"
        ).fetchall()
    assert "ana@example.com" not in stored[0][0]
    reloaded.close()


def test_context_keeps_system_prompt_and_limits_active_window(tmp_path) -> None:
    context = ContextManager(
        tmp_path / "memory.db",
        "Regla permanente",
        max_messages=4,
        max_estimated_tokens=4000,
    )
    for index in range(6):
        context.add_message("user", f"mensaje {index}")

    prompt = context.build_prompt("actual")

    assert "Regla permanente" in prompt
    assert "mensaje 0" not in prompt
    assert "mensaje 5" in prompt
    context.close()


def test_context_compacts_old_messages_with_router(tmp_path) -> None:
    class FakeSummarizer:
        def generar_respuesta(self, _prompt: str) -> RespuestaLLM:
            return RespuestaLLM("hecho importante", "offline", 1, 1, 0.0)

    context = ContextManager(
        tmp_path / "memory.db",
        "Regla permanente",
        max_messages=4,
        summarizer=FakeSummarizer(),
    )
    for index in range(15):
        context.add_message("user", f"mensaje {index}")
    context.compact(FakeSummarizer())

    assert context.summary == "hecho importante"
    assert len(context.messages) <= 4
    context.close()


def test_compaction_includes_previous_summary_in_prompt(tmp_path) -> None:
    prompts: list[str] = []

    class RecordingSummarizer:
        def generar_respuesta(self, prompt: str) -> RespuestaLLM:
            prompts.append(prompt)
            return RespuestaLLM("resumen nuevo", "offline", 1, 1, 0.0)

    summarizer = RecordingSummarizer()
    context = ContextManager(
        tmp_path / "memory.db",
        "Regla permanente",
        max_messages=4,
        summarizer=summarizer,
    )
    for index in range(4):
        context.add_message("user", f"mensaje {index}")
    context.summary = "El proyecto se llama Orion y usa Kubuntu."
    context.add_message("user", "mensaje 4")

    assert "Orion" in prompts[0]
    assert "Kubuntu" in prompts[0]
    context.close()


@pytest.mark.parametrize("role", ["invalid", "tool"])
def test_context_rejects_unknown_roles(tmp_path, role: str) -> None:
    context = ContextManager(tmp_path / "memory.db", "Regla")
    with pytest.raises(ValueError, match="rol"):
        context.add_message(role, "contenido")
    context.close()


def test_retention_purges_archived_sessions_with_messages(tmp_path) -> None:
    database = tmp_path / "memory.db"
    context = ContextManager(database, "Regla", retention_days=1)
    context.add_message("user", "mensaje que debe purgarse")
    archived_session = context.session_id
    context.close()

    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            UPDATE conversation_sessions
            SET archived = 1, last_activity_at = '2020-01-01T00:00:00+00:00'
            WHERE id = ?
            """,
            (archived_session,),
        )
        connection.commit()

    reopened = ContextManager(database, "Regla", retention_days=1)
    reopened.close()

    with sqlite3.connect(database) as connection:
        message_count = connection.execute(
            "SELECT COUNT(*) FROM conversation_messages WHERE session_id = ?",
            (archived_session,),
        ).fetchone()[0]
        session_count = connection.execute(
            "SELECT COUNT(*) FROM conversation_sessions WHERE id = ?",
            (archived_session,),
        ).fetchone()[0]

    assert message_count == 0
    assert session_count == 0


def test_context_starts_new_session_after_timeout(tmp_path) -> None:
    database = tmp_path / "memory.db"
    first = ContextManager(database, "Regla", session_timeout_hours=1)
    first_session = first.session_id
    first.close()

    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            UPDATE conversation_sessions
            SET last_activity_at = '2020-01-01T00:00:00+00:00'
            WHERE id = ?
            """,
            (first_session,),
        )
        connection.commit()

    second = ContextManager(database, "Regla", session_timeout_hours=1)
    assert second.session_id != first_session
    second.close()


def test_context_encrypts_persisted_content_when_key_is_configured(tmp_path) -> None:
    key = Fernet.generate_key().decode()
    database = tmp_path / "memory.db"
    context = ContextManager(database, "Regla", encryption_key=key)
    context.add_message("user", "dato privado")
    context.close()

    with sqlite3.connect(database) as connection:
        stored = connection.execute(
            "SELECT content FROM conversation_messages"
        ).fetchone()[0]
    assert stored != "dato privado"

    restored = ContextManager(database, "Regla", encryption_key=key)
    assert restored.messages[0].content == "dato privado"
    restored.close()


def test_existing_plaintext_database_is_migrated_to_encryption(tmp_path) -> None:
    database = tmp_path / "memory.db"
    plain = ContextManager(database, "Regla")
    plain.add_message("user", "dato heredado")
    plain.close()

    key = Fernet.generate_key().decode()
    encrypted = ContextManager(database, "Regla", encryption_key=key)
    assert encrypted.messages[0].content == "dato heredado"
    encrypted.close()

    with sqlite3.connect(database) as connection:
        stored = connection.execute(
            "SELECT content FROM conversation_messages"
        ).fetchone()[0]
        format_value = connection.execute(
            "SELECT value FROM storage_metadata WHERE key = 'content_format'"
        ).fetchone()[0]
    assert stored != "dato heredado"
    assert format_value == "encrypted"
