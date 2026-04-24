"""
Oráculo de Mesa — Ponto de entrada da aplicação.
"""
from telegram import Update
from telegram.ext import Application

from config import TELEGRAM_TOKEN, logger
from bot.registry import registrar, configurar_menu


def main() -> None:
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN não encontrado. Verifique o .env.")
        return

    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(configurar_menu)
        .build()
    )
    registrar(app)

    logger.info("Oráculo de Mesa iniciado.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
