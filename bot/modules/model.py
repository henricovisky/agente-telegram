"""
Módulo de seleção de modelo de IA.
Permite ao usuário escolher qual modelo do Gemini usar para o chat.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.gemini_service import GeminiService
from services.conversation_service import conversation_service

async def modelo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista os modelos disponíveis com botões para seleção."""
    modelos = GeminiService.get_available_models()
    chat_id = update.effective_chat.id
    atual = conversation_service.get_model(chat_id) or GeminiService.MODELO_CHAT
    
    keyboard = []
    for m in modelos:
        label = f"✅ {m}" if m == atual else m
        keyboard.append([InlineKeyboardButton(label, callback_data=f"set_model:{m}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *Seleção de Modelo*\n\n"
        "Escolha qual modelo o Oráculo deve usar preferencialmente para responder suas mensagens:\n"
        f"_(Atual: `{atual}`)_",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def set_model_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa a escolha do modelo via botão inline."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("set_model:"):
        return
    
    model_name = data.split(":")[1]
    chat_id = update.effective_chat.id
    
    conversation_service.set_model(chat_id, model_name)
    
    await query.edit_message_text(
        f"✅ Modelo alterado para: `{model_name}`\n\n"
        "As próximas mensagens usarão este modelo como primeira opção.",
        parse_mode="Markdown"
    )
