from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from src.context.sanitizer import sanitize_text
from src.context.store import ConversationStore
from src.core.exceptions import RecoverableError
from src.core.llm import GestorPresupuesto, RespuestaLLM
from src.llm.base import ProviderError


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class MessageSummarizer(Protocol):
    def generar_respuesta(self, mensaje: str) -> RespuestaLLM:
        """Genera un resumen compatible con RespuestaLLM."""


class ContextManager:
    """Ventana RAM respaldada por SQLite para una sesión conversacional."""

    def __init__(
        self,
        database_path: str | Path,
        system_prompt: str,
        max_messages: int = 14,
        max_estimated_tokens: int = 4000,
        summarizer: MessageSummarizer | None = None,
        presupuesto: GestorPresupuesto | None = None,
        session_timeout_hours: int = 2,
        encryption_key: str | None = None,
        retention_days: int = 30,
    ) -> None:
        if (
            not isinstance(max_messages, int)
            or isinstance(max_messages, bool)
            or max_messages < 2
            or not isinstance(max_estimated_tokens, int)
            or isinstance(max_estimated_tokens, bool)
            or max_estimated_tokens < 1
        ):
            raise ValueError("Los límites de contexto no son válidos.")
        if not isinstance(system_prompt, str):
            raise TypeError("El system prompt debe ser texto.")
        self.system_prompt = sanitize_text(system_prompt.strip())
        if not self.system_prompt:
            raise ValueError("El system prompt no puede estar vacío.")
        self.max_messages = max_messages
        self.max_estimated_tokens = max_estimated_tokens
        self.summarizer = summarizer
        self.presupuesto = presupuesto
        self.store = ConversationStore(
            database_path,
            session_timeout_hours=session_timeout_hours,
            encryption_key=encryption_key,
            retention_days=retention_days,
        )
        self.session_id, self.summary = self.store.get_or_create_session()
        self.messages = [
            ChatMessage(role, content)
            for role, content in self.store.load_recent_messages(
                self.session_id, max_messages
            )
        ]
        self._trim_window()

    def add_message(self, role: str, content: str) -> None:
        if role not in {"user", "assistant", "system"}:
            raise ValueError("El rol de contexto no es válido.")
        sanitized = sanitize_text(content.strip())
        if not sanitized:
            raise ValueError("El contenido de contexto no puede estar vacío.")
        message = ChatMessage(role, sanitized)
        self.messages.append(message)
        self.store.append_message(self.session_id, role, sanitized)
        if len(self.messages) > self.max_messages and self.summarizer is not None:
            self.compact(self.summarizer)
        self._trim_window()

    def build_prompt(self, user_message: str) -> str:
        """Construye un prompt acotado con instrucciones y memoria activa."""
        sanitized_user = sanitize_text(user_message.strip())
        parts = [f"[SYSTEM]\n{self.system_prompt}"]
        if self.summary:
            parts.append(f"[RESUMEN_PREVIO]\n{self.summary}")
        for message in self.messages:
            parts.append(f"[{message.role.upper()}]\n{message.content}")
        parts.append(f"[USER]\n{sanitized_user}")
        return "\n\n".join(parts)

    def compact(self, summarizer) -> None:
        """Resume los mensajes antiguos con el proveedor recibido."""
        if len(self.messages) <= self.max_messages:
            return
        count = min(6, len(self.messages) - 2)
        old_messages = self.messages[:count]
        fragment = "\n".join(
            f"{message.role}: {message.content}" for message in old_messages
        )
        prompt = (
            "Resume brevemente los hechos y preferencias importantes de esta "
            f"conversación:\n{fragment}"
        )
        try:
            if self.presupuesto is not None:
                self.presupuesto.verificar_disponibilidad()
            summary_response = summarizer.generar_respuesta(prompt)
            if self.presupuesto is not None:
                self.presupuesto.registrar_uso(summary_response)
        except (ProviderError, RecoverableError):
            return
        self.summary = sanitize_text(summary_response.contenido)
        self.store.update_summary(self.session_id, self.summary)
        self.messages = self.messages[count:]
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def _trim_window(self) -> None:
        while (
            len(self.messages) > self.max_messages
            or self._estimated_tokens() > self.max_estimated_tokens
        ):
            if len(self.messages) <= 1:
                break
            self.messages.pop(0)

    def _estimated_tokens(self) -> int:
        return sum(max(1, len(message.content) // 4) for message in self.messages)

    def close(self) -> None:
        self.store.close()

    def clear(self) -> None:
        self.store.clear_session(self.session_id)
        self.messages.clear()
        self.summary = ""
