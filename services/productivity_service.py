"""
Serviço de produtividade: Gerencia Notas e Tarefas no SQLite.
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join("data", "memory.db")

class ProductivityService:
    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(DB_PATH)

    def _init_db(self):
        with self._conn() as conn:
            # Tabela de Notas
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    TEXT NOT NULL,
                    content    TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            # Tabela de Tarefas
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    TEXT NOT NULL,
                    content    TEXT NOT NULL,
                    done       INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)

    # --- Notas ---
    def add_note(self, user_id: str, content: str) -> int:
        with self._conn() as conn:
            cursor = conn.execute(
                "INSERT INTO notes (user_id, content, created_at) VALUES (?,?,?)",
                (user_id, content, datetime.utcnow().isoformat())
            )
            return cursor.lastrowid

    def get_notes(self, user_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, content FROM notes WHERE user_id = ? ORDER BY id DESC",
                (user_id,)
            ).fetchall()
            return [{"id": r[0], "text": r[1]} for r in rows]

    def delete_note(self, user_id: str, note_id: int) -> bool:
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM notes WHERE id = ? AND user_id = ?",
                (note_id, user_id)
            )
            return cursor.rowcount > 0

    # --- Tarefas ---
    def add_task(self, user_id: str, content: str) -> int:
        with self._conn() as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (user_id, content, created_at) VALUES (?,?,?)",
                (user_id, content, datetime.utcnow().isoformat())
            )
            return cursor.lastrowid

    def get_pending_tasks(self, user_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, content FROM tasks WHERE user_id = ? AND done = 0 ORDER BY id ASC",
                (user_id,)
            ).fetchall()
            return [{"id": r[0], "text": r[1]} for r in rows]

    def complete_task(self, user_id: str, task_id: int) -> bool:
        with self._conn() as conn:
            cursor = conn.execute(
                "UPDATE tasks SET done = 1 WHERE id = ? AND user_id = ?",
                (task_id, user_id)
            )
            return cursor.rowcount > 0

# Singleton
productivity_service = ProductivityService()
