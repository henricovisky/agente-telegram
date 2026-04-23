from services.memory_service import memory_service


class TokenManager:
    """Estimativa local de tokens e rastreamento de uso diário."""

    CHARS_PER_TOKEN = 4
    MAX_CHARS_PER_CALL = 120_000  # ~30k tokens

    def estimar(self, texto: str) -> int:
        return len(texto) // self.CHARS_PER_TOKEN

    def dentro_do_limite(self, texto: str) -> bool:
        return len(texto) <= self.MAX_CHARS_PER_CALL

    def registrar_uso(self, model: str, chars_entrada: int, chars_saida: int):
        memory_service.registrar_tokens(
            model,
            chars_entrada // self.CHARS_PER_TOKEN,
            chars_saida // self.CHARS_PER_TOKEN,
        )

    def relatorio_hoje(self) -> str:
        return memory_service.relatorio_tokens_hoje()


# Singleton
token_manager = TokenManager()
