from functools import wraps
from config import ALLOWED_CHAT_IDS, logger


def autorizados_apenas(handler):
    """Decorator: bloqueia usuários não listados em ALLOWED_CHAT_IDS.
    
    Suporta tanto CommandHandler (update.message) quanto
    CallbackQueryHandler (update.callback_query), onde update.message é None.
    """
    @wraps(handler)
    async def wrapper(update, context):
        chat_id = update.effective_chat.id
        if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
            logger.warning(f"Acesso negado: chat_id={chat_id}")
            # Callback queries não têm .message — responde via query.answer
            if update.callback_query:
                await update.callback_query.answer("⛔ Acesso não autorizado.", show_alert=True)
            elif update.message:
                await update.message.reply_text("⛔ Acesso não autorizado.")
            return
        return await handler(update, context)
    return wrapper
