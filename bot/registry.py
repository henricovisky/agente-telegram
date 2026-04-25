from telegram.ext import CommandHandler, MessageHandler, filters

from bot.middleware import autorizados_apenas
from bot.modules import core, rpg, admin, chat, monitoring, persona, model
from telegram import BotCommand, BotCommandScopeAllPrivateChats, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

# Lista de comandos para o menu (BotCommand)
COMANDOS_MENU = [
    BotCommand("start", "Início e boas-vindas"),
    BotCommand("ajuda", "Lista completa de comandos"),
    BotCommand("status", "Tokens usados hoje"),
    BotCommand("status_server", "Status do hardware"),
    BotCommand("modelo", "Selecionar modelo IA"),
    BotCommand("persona", "Trocar personalidade"),
    BotCommand("memoria", "Ver contexto do chat"),
    BotCommand("memoria_limpar", "Limpar histórico"),
    BotCommand("rpg_transcrever", "Transcrever áudio Drive"),
    BotCommand("rpg_resumo", "Gerar Crônica PDF"),
    BotCommand("logs", "Ver logs do servidor"),
    BotCommand("update", "Atualizar via GitHub"),
    # Atalhos rápidos de personas
    BotCommand("henricovisky", "Persona: Especialista Linux/Python"),
    BotCommand("mestre", "Persona: Mestre de RPG"),
    BotCommand("dev", "Persona: Senior Developer"),
    BotCommand("financeiro", "Persona: Analista Financeiro"),
    BotCommand("curto", "Persona: Modo Direto"),
]


async def configurar_menu(app):
    """Define a lista de comandos que aparece no menu do Telegram (escopo privado)."""
    await app.bot.set_my_commands(
        COMANDOS_MENU,
        scope=BotCommandScopeAllPrivateChats()
    )


def registrar(app):
    """Registra todos os comandos e handlers disponíveis no bot."""

    # --- Core ---
    app.add_handler(CommandHandler("start",          autorizados_apenas(core.start)))
    app.add_handler(CommandHandler("ajuda",          autorizados_apenas(core.ajuda)))
    app.add_handler(CommandHandler("status",         autorizados_apenas(core.status)))
    app.add_handler(CommandHandler("status_server",  autorizados_apenas(core.status_server)))
    app.add_handler(CommandHandler("update",         autorizados_apenas(admin.update)))
    app.add_handler(CommandHandler("memoria",        autorizados_apenas(core.memoria)))
    app.add_handler(CommandHandler("memoria_limpar", autorizados_apenas(core.memoria_limpar)))

    # --- Módulo RPG ---
    app.add_handler(CommandHandler("rpg_transcrever", autorizados_apenas(rpg.rpg_transcrever)))
    app.add_handler(CommandHandler("rpg_resumo",      autorizados_apenas(rpg.rpg_resumo)))
    app.add_handler(CommandHandler("logs",            autorizados_apenas(monitoring.logs)))
    app.add_handler(CommandHandler("persona",         autorizados_apenas(persona.persona_cmd)))
    app.add_handler(CommandHandler("modelo",          autorizados_apenas(model.modelo_cmd)))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(autorizados_apenas(model.set_model_callback), pattern="^set_model:"))
    
    # Atalhos de personas
    from agent.persona_registry import PERSONAS
    for p_key in PERSONAS.keys():
        app.add_handler(CommandHandler(p_key, autorizados_apenas(persona.trocar_persona)))

    # --- Chat livre (deve ser o ÚLTIMO handler para não interceptar comandos) ---
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            autorizados_apenas(chat.responder),
        )
    )

    # --- Novos módulos: adicione aqui ---
    # --- Jobs em Segundo Plano ---
    if app.job_queue:
        # Executa a cada 10 minutos (600 segundos)
        app.job_queue.run_repeating(monitoring.monitoramento_job, interval=600, first=10)

    # from bot.modules import reuniao
    # app.add_handler(CommandHandler("reuniao_resumo", autorizados_apenas(reuniao.resumo)))
