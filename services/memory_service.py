import sqlite3
import os
from datetime import date

DB_PATH = os.path.join("data", "memory.db")


class MemoryService:
    """Persistência leve em SQLite para rastreamento de tokens."""

    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(DB_PATH)

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS token_usage (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    date          TEXT    NOT NULL,
                    model         TEXT    NOT NULL,
                    input_tokens  INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_facts (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     TEXT    NOT NULL,
                    fact        TEXT    NOT NULL,
                    embedding   BLOB    NOT NULL,
                    created_at  TEXT    NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_user ON user_facts(user_id)")

    def registrar_tokens(self, model: str, input_tokens: int, output_tokens: int):
        today = date.today().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO token_usage (date, model, input_tokens, output_tokens) VALUES (?,?,?,?)",
                (today, model, input_tokens, output_tokens)
            )

    def relatorio_tokens_hoje(self) -> str:
        today = date.today().isoformat()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT model, SUM(input_tokens), SUM(output_tokens) "
                "FROM token_usage WHERE date=? GROUP BY model",
                (today,)
            ).fetchall()
        if not rows:
            return "Sem uso hoje."
        return "\n".join(f"  {m}: {i}in / {o}out tokens" for m, i, o in rows)

    # --- RAG / Long Term Memory ---

    def salvar_fato(self, user_id: str, fact: str, embedding: list[float]):
        import json
        from datetime import datetime
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO user_facts (user_id, fact, embedding, created_at) VALUES (?,?,?,?)",
                (user_id, fact, json.dumps(embedding), datetime.utcnow().isoformat())
            )

    def buscar_fatos(self, user_id: str) -> list[dict]:
        import json
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT fact, embedding FROM user_facts WHERE user_id = ?",
                (user_id,)
            ).fetchall()
        return [{"fact": r["fact"], "embedding": json.loads(r["embedding"])} for r in rows]


# Singleton
memory_service = MemoryService()
