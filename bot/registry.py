from telegram.ext import CommandHandler

from bot.middleware import autorizados_apenas
from bot.modules import core, rpg, admin


def registrar(app):
    """Registra todos os comandos disponíveis no bot."""

    # --- Core ---
    app.add_handler(CommandHandler("start",          autorizados_apenas(core.start)))
    app.add_handler(CommandHandler("ajuda",          autorizados_apenas(core.ajuda)))
    app.add_handler(CommandHandler("status",         autorizados_apenas(core.status)))
    app.add_handler(CommandHandler("status_server",  autorizados_apenas(core.status_server)))
    app.add_handler(CommandHandler("update",          autorizados_apenas(admin.update)))
    app.add_handler(CommandHandler("memoria",        autorizados_apenas(core.memoria)))
    app.add_handler(CommandHandler("memoria_limpar", autorizados_apenas(core.memoria_limpar)))


    # --- Módulo RPG ---
    app.add_handler(CommandHandler("rpg_transcrever", autorizados_apenas(rpg.rpg_transcrever)))
    app.add_handler(CommandHandler("rpg_resumo",      autorizados_apenas(rpg.rpg_resumo)))

    # --- Novos módulos: adicione aqui ---
    # from bot.modules import reuniao
    # app.add_handler(CommandHandler("reuniao_resumo", autorizados_apenas(reuniao.resumo)))
