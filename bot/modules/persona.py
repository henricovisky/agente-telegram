"""
Módulo de gerenciamento de personas.
Permite listar e trocar a personalidade do agente via botões inline
ou via atalhos diretos (/dev, /mestre, etc.).
"""
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from agent.persona_registry import PERSONAS, list_personas
from services.conversation_service import conversation_service


def _build_persona_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Monta teclado inline com todas as personas disponíveis."""
    atual = conversation_service.get_persona(chat_id)
    rows = []
    for key, data in PERSONAS.items():
        emoji = data.get("emoji", "🧠")
        name  = data.get("name", key)
        label = f"✅ {emoji} {name}" if key == atual else f"{emoji} {name}"
        rows.append([InlineKeyboardButton(label, callback_data=f"set_persona:{key}")])
    return InlineKeyboardMarkup(rows)


async def persona_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe menu de personas com botões inline para seleção."""
    chat_id = update.effective_chat.id
    atual   = conversation_service.get_persona(chat_id) or "padrão"
    p_atual = PERSONAS.get(atual, {})
    nome_atual = p_atual.get("name", atual)

    await update.message.reply_text(
        f"🧠 <b>Gerenciamento de Personas</b>\n\n"
        f"Persona atual: <b>{html.escape(nome_atual)}</b>\n\n"
        "Selecione uma personalidade para o agente:",
        parse_mode="HTML",
        reply_markup=_build_persona_keyboard(chat_id),
    )


async def set_persona_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa seleção de persona via botão inline."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("set_persona:"):
        return

    key     = data.split(":", 1)[1]
    chat_id = update.effective_chat.id

    if key not in PERSONAS:
        await query.edit_message_text("❌ Persona não encontrada.")
        return

    conversation_service.set_persona(chat_id, key)
    p = PERSONAS[key]

    await query.edit_message_text(
        f"✅ Persona alterada para: <b>{html.escape(p.get('name', key))}</b>\n\n"
        f"<i>{html.escape(p.get('description', ''))}</i>\n\n"
        "Use /persona para trocar novamente.",
        parse_mode="HTML",
    )


async def trocar_persona(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Troca persona via atalho direto (/mestre, /dev, etc.)."""
    comando = update.message.text.split()[0].replace("/", "").split("@")[0]

    if comando not in PERSONAS:
        await update.message.reply_text("❌ Persona não encontrada.")
        return

    chat_id = update.effective_chat.id
    conversation_service.set_persona(chat_id, comando)
    p = PERSONAS[comando]

    await update.message.reply_text(
        f"✅ Persona alterada para: <b>{html.escape(p.get('name', comando))}</b>\n\n"
        f"<i>{html.escape(p.get('description', ''))}</i>",
        parse_mode="HTML",
    )
