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
import re
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from services.gemini_service import GeminiService
from services.conversation_service import conversation_service
from services.input_handler import InputHandler
from services.output_handler import output_handler
from config import logger

_gemini = GeminiService()
_input_handler = InputHandler(_gemini)


async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler principal que agora suporta Texto, Áudio e Documentos (PDF/MD).
    Implementa o fluxo de Agent Loop com entrada/saída multimídia.
    """
    chat_id = update.effective_chat.id
    message = update.message
    
    # 1. Identifica e processa o tipo de Input
    texto_input = ""
    requires_audio_reply = False
    
    if message.text:
        texto_input = message.text
        # Verifica se o usuário pediu áudio explicitamente no texto
        if re.search(r"(responda|fale|diga) (em|por) (áudio|voz)", texto_input.lower()):
            requires_audio_reply = True
            
    elif message.voice or message.audio:
        texto_input, requires_audio_reply = await _input_handler.process_voice_or_audio(update, context)
        
    elif message.document:
        texto_input = await _input_handler.process_document(update, context)
        # Documentos geralmente não pedem resposta em áudio a menos que o caption peça
        caption = message.caption or ""
        if re.search(r"(responda|fale|diga) (em|por) (áudio|voz)", caption.lower()):
            requires_audio_reply = True
            texto_input += f"\n\nInstrução adicional: {caption}"

    if not texto_input:
        return

    # 2. Sinaliza processamento
    action = ChatAction.RECORD_VOICE if requires_audio_reply else ChatAction.TYPING
    await context.bot.send_chat_action(chat_id=chat_id, action=action)

    try:
        # Recupera histórico persistido
        historico = conversation_service.get_history(chat_id)

        # Persiste a mensagem do usuário (ou transcrição)
        conversation_service.add_message(chat_id, "user", texto_input)

        async def _keep_acting():
            while True:
                await asyncio.sleep(4)
                try:
                    await context.bot.send_chat_action(chat_id=chat_id, action=action)
                except Exception:
                    break

        async def _on_thought(thought_text: str):
            """Exibe o raciocínio do agente em tempo real."""
            # O usuário solicitou não ver o raciocínio.
            # logger.debug(f"Thought: {thought_text}")
            pass

        acting_task = asyncio.create_task(_keep_acting())
        try:
            resposta = await _gemini.chat(texto_input, chat_id, historico, on_thought=_on_thought)
        finally:
            acting_task.cancel()

        # 3. Persiste a resposta
        conversation_service.add_message(chat_id, "assistant", resposta)

        # 4. Envia resposta via OutputHandler (Chunking/TTS)
        await output_handler.send_output(update, context, resposta, requires_audio=requires_audio_reply)

    except Exception as e:
        logger.error(f"Erro no handler de chat: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Falha ao processar sua mensagem: {str(e)[:300]}"
        )
