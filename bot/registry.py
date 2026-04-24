from telegram.ext import CommandHandler, MessageHandler, filters

from bot.middleware import autorizados_apenas
from bot.modules import core, rpg, admin, chat, monitoring, persona
from telegram import BotCommand

# Lista de comandos para o menu (BotCommand)
COMANDOS_MENU = [
    BotCommand("start", "Boas-vindas e lista de módulos"),
    BotCommand("ajuda", "Todos os comandos disponíveis"),
    BotCommand("status", "Tokens Gemini usados hoje"),
    BotCommand("status_server", "Métricas do servidor (CPU, RAM, Rede)"),
    BotCommand("memoria", "Ver histórico do chat"),
    BotCommand("memoria_limpar", "Apagar histórico e iniciar nova conversa"),
    BotCommand("rpg_transcrever", "Transcrever áudio de RPG do Drive"),
    BotCommand("rpg_resumo", "Gerar Crônica Épica em PDF"),
    BotCommand("logs", "Ver últimos logs do sistema"),
    BotCommand("persona", "Mudar personalidade do agente"),
    BotCommand("update", "Atualizar bot via GitHub"),
]


async def configurar_menu(app):
    """Define a lista de comandos que aparece no menu do Telegram."""
    await app.bot.set_my_commands(COMANDOS_MENU)


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
