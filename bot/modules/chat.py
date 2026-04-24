"""
Módulo de chat livre — intercepta mensagens de texto comuns (não-comandos)
e as envia ao Gemini com histórico persistido em SQLite.

Fluxo (PRD §6.2):
  1. Mensagem chega → middleware já validou autorização.
  2. Bot exibe "digitando..." (Chat Action).
  3. Histórico é recuperado do ConversationService.
  4. Gemini gera resposta via GeminiService.chat().
  5. Mensagem e resposta são persistidas.
  6. Resposta é enviada ao chat.
"""
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from services.gemini_service import GeminiService
from services.conversation_service import conversation_service
from config import logger

_gemini = GeminiService()


async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler principal de mensagens de texto livres.
    Mantém histórico multi-turno persistido em SQLite.
    """
    mensagem = update.message.text
    if not mensagem:
        return

    chat_id = update.effective_chat.id

    # Sinaliza "digitando..." continuamente enquanto processa
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        # Recupera histórico persistido (últimas N mensagens)
        historico = conversation_service.get_history(chat_id)

        # Persiste a mensagem do usuário antes de chamar o LLM
        conversation_service.add_message(chat_id, "user", mensagem)

        # Chama o LLM — pode demorar; reenvia typing a cada 4s para não expirar
        async def _keep_typing():
            while True:
                await asyncio.sleep(4)
                try:
                    await context.bot.send_chat_action(
                        chat_id=chat_id, action=ChatAction.TYPING
                    )
                except Exception:
                    break

        typing_task = asyncio.create_task(_keep_typing())
        try:
            resposta = await _gemini.chat(mensagem, historico)
        finally:
            typing_task.cancel()

        # Persiste a resposta do assistente
        conversation_service.add_message(chat_id, "assistant", resposta)

        # Envia ao Telegram (split automático se > 4096 chars)
        if len(resposta) <= 4096:
            await update.message.reply_text(resposta)
        else:
            for i in range(0, len(resposta), 4096):
                await update.message.reply_text(resposta[i : i + 4096])

    except Exception as e:
        logger.error(f"Erro no handler de chat: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Falha ao processar sua mensagem: {str(e)[:300]}"
        )
