"""
Serviço de persistência de conversas em SQLite.
Implementa o modelo de dados do PRD (seção 9):
  - conversations: id, user_id, provider
  - messages: conversation_id, role, content
"""
import sqlite3
import os
import uuid
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join("data", "memory.db")
MAX_HISTORY = 20  # máximo de mensagens a recuperar por conversa


class ConversationService:
    """
    Repositório de conversas e mensagens para o agente.
    Cada user_id tem exatamente uma conversa ativa por vez.
    """

    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # WAL mode: melhor performance com múltiplas leituras simultâneas
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id       TEXT PRIMARY KEY,
                    user_id  TEXT NOT NULL,
                    provider TEXT NOT NULL DEFAULT 'gemini',
                    persona  TEXT NOT NULL DEFAULT 'henricovisky',
                    model    TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            try:
                conn.execute("ALTER TABLE conversations ADD COLUMN model TEXT")
            except sqlite3.OperationalError:
                pass # Coluna já existe
            try:
                conn.execute("ALTER TABLE conversations ADD COLUMN persona TEXT NOT NULL DEFAULT 'henricovisky'")
            except sqlite3.OperationalError:
                pass # Coluna já existe
            try:
                conn.execute("ALTER TABLE conversations ADD COLUMN provider TEXT NOT NULL DEFAULT 'gemini'")
            except sqlite3.OperationalError:
                pass # Coluna já existe
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role            TEXT NOT NULL,
                    content         TEXT NOT NULL,
                    created_at      TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id)"
            )

    # ------------------------------------------------------------------
    # Conversas
    # ------------------------------------------------------------------

    def get_or_create_conversation(self, user_id: int, provider: str = "gemini") -> str:
        """
        Retorna o ID da conversa ativa do usuário, criando uma se não existir.
        """
        uid = str(user_id)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM conversations WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                (uid,),
            ).fetchone()
            if row:
                return row["id"]
            conv_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO conversations (id, user_id, provider, persona, created_at) VALUES (?,?,?,?,?)",
                (conv_id, uid, provider, 'henricovisky', datetime.utcnow().isoformat()),
            )
            return conv_id

    def reset_conversation(self, user_id: int, provider: str = "gemini") -> str:
        """
        Apaga a conversa ativa e abre uma nova (equivale a /memoria_limpar).
        """
        uid = str(user_id)
        with self._conn() as conn:
            old = conn.execute(
                "SELECT id FROM conversations WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                (uid,),
            ).fetchone()
            if old:
                conn.execute("DELETE FROM messages WHERE conversation_id = ?", (old["id"],))
                conn.execute("DELETE FROM conversations WHERE id = ?", (old["id"],))
            conv_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO conversations (id, user_id, provider, created_at) VALUES (?,?,?,?)",
                (conv_id, uid, provider, datetime.utcnow().isoformat()),
            )
            return conv_id

    def get_persona(self, user_id: int) -> str:
        """Retorna a persona atual da conversa ativa."""
        uid = str(user_id)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT persona FROM conversations WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                (uid,),
            ).fetchone()
            return row["persona"] if row else "henricovisky"

    def set_persona(self, user_id: int, persona_key: str):
        """Atualiza a persona da conversa ativa."""
        conv_id = self.get_or_create_conversation(user_id)
        with self._conn() as conn:
            conn.execute(
                "UPDATE conversations SET persona = ? WHERE id = ?",
                (persona_key, conv_id),
            )

    def get_model(self, user_id: int) -> Optional[str]:
        """Retorna o modelo preferido da conversa ativa."""
        uid = str(user_id)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT model FROM conversations WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                (uid,),
            ).fetchone()
            return row["model"] if row else None

    def set_model(self, user_id: int, model_name: str):
        """Atualiza o modelo da conversa ativa."""
        conv_id = self.get_or_create_conversation(user_id)
        with self._conn() as conn:
            conn.execute(
                "UPDATE conversations SET model = ? WHERE id = ?",
                (model_name, conv_id),
            )

    # ------------------------------------------------------------------
    # Mensagens
    # ------------------------------------------------------------------

    def add_message(self, user_id: int, role: str, content: str):
        """Adiciona uma mensagem à conversa ativa do usuário."""
        conv_id = self.get_or_create_conversation(user_id)
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?,?,?,?)",
                (conv_id, role, content, datetime.utcnow().isoformat()),
            )

    def get_history(self, user_id: int, limit: int = MAX_HISTORY) -> list[dict]:
        """
        Retorna as últimas `limit` mensagens da conversa ativa.
        Formato: [{"role": "user"|"assistant"|"system", "content": "..."}]
        """
        conv_id = self.get_or_create_conversation(user_id)
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages "
                "WHERE conversation_id = ? "
                "ORDER BY id DESC LIMIT ?",
                (conv_id, limit),
            ).fetchall()
        # retorna em ordem cronológica
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    def get_history_string(self, user_id: int, limit: int = MAX_HISTORY) -> str:
        """Formata o histórico como texto legível para exibição."""
        turns = self.get_history(user_id, limit)
        if not turns:
            return ""
        return "\n".join(f"{t['role'].upper()}: {t['content']}" for t in turns)

    def count_messages(self, user_id: int) -> int:
        conv_id = self.get_or_create_conversation(user_id)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM messages WHERE conversation_id = ?",
                (conv_id,),
            ).fetchone()
        return row["n"] if row else 0


# Singleton
conversation_service = ConversationService()
