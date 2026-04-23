from functools import wraps
from config import ALLOWED_CHAT_IDS, logger


def autorizados_apenas(handler):
    """Decorator: bloqueia usuários não listados em ALLOWED_CHAT_IDS."""
    @wraps(handler)
    async def wrapper(update, context):
        chat_id = update.effective_chat.id
        if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
            await update.message.reply_text("⛔ Acesso não autorizado.")
            logger.warning(f"Acesso negado: chat_id={chat_id}")
            return
        return await handler(update, context)
    return wrapper
