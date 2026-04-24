"""
Módulo de gerenciamento de personas.
Permite listar e trocar a personalidade do agente via comandos /persona ou /[nome_da_persona].
"""
from telegram import Update
from telegram.ext import ContextTypes
from agent.persona_registry import PERSONAS, list_personas
from services.conversation_service import conversation_service

async def persona_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista as personas disponíveis e explica como trocar."""
    lista = list_personas()
    await update.message.reply_text(
        "🧠 *Gerenciamento de Personas*\n\n"
        "Escolha uma personalidade para o agente. Para trocar, use o comando correspondente:\n\n"
        f"{lista}\n\n"
        "Exemplo: `/dev` para mudar para modo Senior Developer.",
        parse_mode="Markdown"
    )

async def trocar_persona(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Troca a persona baseada no comando enviado (ex: /mestre)."""
    # O comando vem como /mestre, /dev, etc.
    comando = update.message.text.split()[0].replace("/", "")
    
    if comando in PERSONAS:
        chat_id = update.effective_chat.id
        conversation_service.set_persona(chat_id, comando)
        p = PERSONAS[comando]
        await update.message.reply_text(
            f"✅ Persona alterada para: *{p['name']}*\n\n_{p['description']}_",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Persona não encontrada.")
