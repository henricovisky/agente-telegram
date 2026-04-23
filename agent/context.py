from collections import defaultdict


class ContextManager:
    """Memória de conversa em RAM por chat_id (últimos N turnos)."""

    MAX_TURNS = 5

    def __init__(self):
        self._history: dict[int, list[dict]] = defaultdict(list)

    def add_turn(self, chat_id: int, role: str, content: str):
        turns = self._history[chat_id]
        turns.append({"role": role, "content": content[:500]})
        self._history[chat_id] = turns[-self.MAX_TURNS:]

    def get_context_string(self, chat_id: int) -> str:
        turns = self._history.get(chat_id, [])
        if not turns:
            return ""
        return "\n".join(f"{t['role'].upper()}: {t['content']}" for t in turns)

    def clear(self, chat_id: int):
        self._history.pop(chat_id, None)

    def info(self, chat_id: int) -> str:
        n = len(self._history.get(chat_id, []))
        return f"{n} turno(s) guardado(s)."


# Singleton compartilhado por todos os módulos
context_manager = ContextManager()
