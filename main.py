"""
Oráculo de Mesa — Ponto de entrada da aplicação.

Este ficheiro é responsável por inicializar o bot Telegram,
registar os handlers de comandos e iniciar o loop de polling.
"""

from telegram import Update
from telegram.ext import Application, CommandHandler

from config import TELEGRAM_TOKEN, logger
from bot.handlers import BotHandlers


def main() -> None:
    """
    Ponto de entrada principal da aplicação.
    Constrói a aplicação Telegram, regista os comandos
    disponíveis e inicia o servidor de polling.
    """
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN não encontrado. Verifique o ficheiro .env.")
        return

    # Inicializa os handlers que contêm a lógica de negócio
    handlers = BotHandlers()

    # Constrói a aplicação do bot com o token fornecido
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Regista os comandos disponíveis
    app.add_handler(CommandHandler("rpg_resumo", handlers.rpg_resumo))

    logger.info("Oráculo de Mesa a iniciar... Aguardando comandos.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
