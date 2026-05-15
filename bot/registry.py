from telegram.ext import CommandHandler, MessageHandler, filters

from bot.middleware import autorizados_apenas
from bot.modules import core, rpg, admin, chat, monitoring, persona, model, productivity, concurso, server
from telegram import BotCommand, BotCommandScopeAllPrivateChats, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

# Lista de comandos para o menu (BotCommand)
COMANDOS_MENU = [
    BotCommand("start", "Início e boas-vindas"),
    BotCommand("ajuda", "Guia completo de comandos"),
    BotCommand("concurso", "Busca concursos do PCI"),
    BotCommand("status", "Tokens e uso hoje"),
    BotCommand("status_server", "Hardware e rede"),
    BotCommand("modelo", "Trocar modelo de IA"),
    BotCommand("persona", "Trocar personalidade"),
    BotCommand("memoria", "Contexto atual"),
    BotCommand("memoria_limpar", "Resetar conversa"),
    BotCommand("nota", "Salvar nota: /nota <texto>"),
    BotCommand("notas", "Listar minhas notas"),
    BotCommand("task", "Gerenciar tarefas"),
    BotCommand("briefing", "Resumo do dia"),
    BotCommand("server", "Gestão do servidor e rede"),
    BotCommand("rpg_transcrever", "Transcrever áudio Drive"),
    BotCommand("rpg_resumo", "Gerar PDF da sessão"),
    BotCommand("logs", "Ver logs do servidor"),
    BotCommand("update", "Atualizar via GitHub"),
    # Atalhos rápidos de personas
    BotCommand("henricovisky", "Persona: Especialista"),
    BotCommand("mestre", "Persona: Mestre RPG"),
    BotCommand("dev", "Persona: Senior Dev"),
    BotCommand("financeiro", "Persona: Analista"),
    BotCommand("curto", "Persona: Direto"),
]


async def configurar_menu(app):
    """Define a lista de comandos que aparece no menu do Telegram (escopo privado)."""
    from config import logger
    try:
        await app.bot.set_my_commands(
            COMANDOS_MENU,
            scope=BotCommandScopeAllPrivateChats()
        )
        logger.info("✅ Menu de comandos atualizado com sucesso.")
    except Exception as e:
        logger.error(f"❌ Erro ao configurar menu: {e}")


def registrar(app):
    """Registra todos os comandos e handlers disponíveis no bot."""

    # --- Core ---
    app.add_handler(CommandHandler("start",          autorizados_apenas(core.start)))
    app.add_handler(CommandHandler("ajuda",          autorizados_apenas(core.ajuda)))
    app.add_handler(CommandHandler("status",         autorizados_apenas(core.status)))
    app.add_handler(CommandHandler("status_server",  autorizados_apenas(server.status_server_cmd)))  # alias → painel /server
    app.add_handler(CommandHandler("update",         autorizados_apenas(admin.update)))
    app.add_handler(CommandHandler("memoria",        autorizados_apenas(core.memoria)))
    app.add_handler(CommandHandler("memoria_limpar", autorizados_apenas(core.memoria_limpar)))

    # --- Módulo RPG ---
    app.add_handler(CommandHandler("rpg_transcrever", autorizados_apenas(rpg.rpg_transcrever)))
    app.add_handler(CommandHandler("rpg_resumo",      autorizados_apenas(rpg.rpg_resumo)))
    app.add_handler(CommandHandler("logs",            autorizados_apenas(server.logs_cmd)))           # alias → painel /server
    app.add_handler(CommandHandler("persona",         autorizados_apenas(persona.persona_cmd)))
    app.add_handler(CommandHandler("modelo",          autorizados_apenas(model.modelo_cmd)))

    # Callbacks inline
    app.add_handler(CallbackQueryHandler(autorizados_apenas(model.set_model_callback),    pattern="^set_model:"))
    app.add_handler(CallbackQueryHandler(autorizados_apenas(persona.set_persona_callback), pattern="^set_persona:"))
    
    # --- Produtividade ---
    app.add_handler(CommandHandler("nota",        autorizados_apenas(productivity.nota)))
    app.add_handler(CommandHandler("notas",       autorizados_apenas(productivity.notas)))
    app.add_handler(CommandHandler("nota_apagar", autorizados_apenas(productivity.nota_apagar)))
    app.add_handler(CommandHandler("task",        autorizados_apenas(productivity.task)))
    app.add_handler(CommandHandler("briefing",    autorizados_apenas(productivity.briefing)))

    # --- Concursos ---
    app.add_handler(CommandHandler("concurso",    autorizados_apenas(concurso.concurso_cmd)))

    # --- Infraestrutura ---
    app.add_handler(CommandHandler("server",         autorizados_apenas(server.server_cmd)))
    app.add_handler(CommandHandler("servidor",       autorizados_apenas(server.server_cmd)))
    app.add_handler(CommandHandler("skill_servidor", autorizados_apenas(server.server_cmd)))
    app.add_handler(CallbackQueryHandler(autorizados_apenas(server.server_callback), pattern="^srv:"))

    # Atalhos de personas
    from agent.persona_registry import PERSONAS
    for p_key in PERSONAS.keys():
        app.add_handler(CommandHandler(p_key, autorizados_apenas(persona.trocar_persona)))

    # --- Chat livre (Texto, Voz, Áudio, Documentos) ---
    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.VOICE | filters.AUDIO | filters.Document.ALL) & ~filters.COMMAND,
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
