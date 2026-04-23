import os
import time
import datetime
import psutil
from telegram import Update
from telegram.ext import ContextTypes

from agent.context import context_manager
from agent.token_manager import token_manager

# Registra o momento em que o bot foi iniciado
_BOT_START = time.time()


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _fmt_uptime(seconds: float) -> str:
    d = datetime.timedelta(seconds=int(seconds))
    days = d.days
    h, rem = divmod(d.seconds, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if h:
        parts.append(f"{h}h")
    parts.append(f"{m}m {s}s")
    return " ".join(parts)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧠 *Oráculo de Mesa* — Agente IA Pessoal\n\n"
        "*Core:*\n"
        "/ajuda — lista de comandos\n"
        "/status — uso de tokens hoje\n"
        "/status\\_server — métricas do servidor\n"
        "/update — atualiza o bot via GitHub\n"
        "/memoria — histórico do chat\n"
        "/memoria\\_limpar — apagar histórico\n\n"
        "*Módulo RPG:*\n"
        "/rpg\\_transcrever — transcreve o áudio mais recente do Drive\n"
        "/rpg\\_resumo — gera Crônica Épica em PDF a partir da transcrição",
        parse_mode="Markdown",
    )


async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Comandos disponíveis*\n\n"
        "*/start* — boas-vindas\n"
        "*/ajuda* — esta mensagem\n"
        "*/status* — tokens usados hoje + estado do contexto\n"
        "*/status\\_server* — métricas de CPU, RAM, Disco e rede do servidor\n"
        "*/update* — git pull + pip install + reinício automático\n"
        "*/memoria* — mostra histórico do chat atual\n"
        "*/memoria\\_limpar* — apaga histórico do chat\n\n"
        "*/rpg\\_transcrever* — baixa o áudio mais recente do Drive e gera `.txt`\n"
        "*/rpg\\_resumo* — lê o `.txt` mais recente e gera PDF da Crônica Épica",
        parse_mode="Markdown",
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    relatorio = token_manager.relatorio_hoje()
    ctx_info = context_manager.info(chat_id)
    await update.message.reply_text(
        f"📊 *Status do Agente*\n\n"
        f"*Tokens hoje:*\n{relatorio}\n\n"
        f"*Contexto:* {ctx_info}",
        parse_mode="Markdown",
    )


async def status_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # CPU
    cpu_pct = psutil.cpu_percent(interval=0.5)
    cpu_count = psutil.cpu_count(logical=True)

    # RAM
    ram = psutil.virtual_memory()
    ram_used = _fmt_bytes(ram.used)
    ram_total = _fmt_bytes(ram.total)

    # Disco (raiz do sistema)
    disk = psutil.disk_usage("/")
    disk_used = _fmt_bytes(disk.used)
    disk_total = _fmt_bytes(disk.total)

    # Uptime do sistema operacional
    sys_uptime = time.time() - psutil.boot_time()

    # Uptime do bot (processo atual)
    bot_uptime = time.time() - _BOT_START

    # Processo Python atual (RAM do bot)
    proc = psutil.Process(os.getpid())
    bot_ram = _fmt_bytes(proc.memory_info().rss)

    # Load average (Linux) ou CPU percent (Windows)
    try:
        load = os.getloadavg()
        load_str = f"{load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}"
    except AttributeError:
        load_str = f"{cpu_pct}% (Windows — sem load avg)"

    msg = (
        "🖥️ *Status do Servidor*\n\n"
        f"⏱ *Uptime SO:* `{_fmt_uptime(sys_uptime)}`\n"
        f"🤖 *Uptime Bot:* `{_fmt_uptime(bot_uptime)}`\n\n"
        f"🧠 *CPU:* `{cpu_pct}%` ({cpu_count} cores)\n"
        f"📈 *Load avg (1/5/15m):* `{load_str}`\n\n"
        f"💾 *RAM total:* `{ram_total}`\n"
        f"   Usada: `{ram_used}` ({ram.percent}%)\n"
        f"   Bot:   `{bot_ram}`\n\n"
        f"💿 *Disco (/):* `{disk_used}` / `{disk_total}` ({disk.percent}%)\n"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


async def memoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ctx_str = context_manager.get_context_string(chat_id)
    if not ctx_str:
        await update.message.reply_text("Sem histórico guardado.")
        return
    await update.message.reply_text(
        f"🧠 *Contexto atual:*\n\n{ctx_str[:3000]}",
        parse_mode="Markdown",
    )


async def memoria_limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context_manager.clear(update.effective_chat.id)
    await update.message.reply_text("✅ Histórico apagado.")
