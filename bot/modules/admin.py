"""
Módulo admin — comandos de manutenção do bot.
/update : git pull + pip install + reinício do processo
"""
import asyncio
import os
import sys
import subprocess
from functools import partial

from telegram import Update
from telegram.ext import ContextTypes

from config import logger


async def _subprocess(cmd: list[str], timeout: int = 180) -> tuple[int, str, str]:
    """Executa um comando em thread separada sem bloquear o event loop."""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        partial(subprocess.run, cmd, capture_output=True, text=True, timeout=timeout),
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


async def _reiniciar(delay: float = 3.0):
    """Aguarda `delay` segundos e substitui o processo atual (os.execv)."""
    await asyncio.sleep(delay)
    logger.info("Reiniciando processo via os.execv...")
    os.execv(sys.executable, [sys.executable] + sys.argv)


async def update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /update
    1. git pull origin (branch atual)
    2. pip install -r requirements.txt
    3. Reinicia o processo do bot
    """
    chat_id = update.effective_chat.id

    await update.message.reply_text("🔄 Iniciando atualização...")

    # --- 1. git pull ---
    code, out, err = await _subprocess(["git", "pull"], timeout=60)
    if code != 0:
        await update.message.reply_text(
            f"❌ `git pull` falhou:\n```\n{(err or out)[:500]}\n```",
            parse_mode="Markdown",
        )
        return
    git_msg = out if out else "Já na versão mais recente."

    # --- 2. pip install ---
    pip_cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"]
    code, _, pip_err = await _subprocess(pip_cmd, timeout=180)
    if code == 0:
        pip_msg = "✅ Pacotes atualizados."
    else:
        pip_msg = f"⚠️ pip retornou erros:\n`{pip_err[:300]}`"

    # --- 3. Confirma e agenda reinício ---
    await update.message.reply_text(
        f"✅ *Atualização concluída!*\n\n"
        f"*git pull:*\n`{git_msg[:400]}`\n\n"
        f"*pip install:* {pip_msg}\n\n"
        f"♻️ Reiniciando em 3s...",
        parse_mode="Markdown",
    )

    asyncio.create_task(_reiniciar(delay=3.0))
