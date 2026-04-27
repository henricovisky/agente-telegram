import os
import time
import datetime
import psutil
from telegram import Update
from telegram.ext import ContextTypes

from agent.context import context_manager
from agent.token_manager import token_manager
from services.conversation_service import conversation_service

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
        "🧠 *Henricovisky* — Agente IA Pessoal\n\n"
        "Sou seu assistente inteligente operando com Gemini e memória persistente (RAG).\n\n"
        "🎙️ *Multimídia:* Pode me enviar textos, áudios (transcrevo e respondo em voz) ou documentos (PDF/MD).\n\n"
        "📖 Use /ajuda para ver o guia completo de comandos.",
        parse_mode="Markdown",
    )


async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📖 *Guia de Comandos Henricovisky*\n\n"
        "*Qualquer texto/voz* — Conversa com o agente (Gemini + RAG)\n"
        "*PDF/MD* — Envie arquivos para análise\n\n"
        "🛠 *Sistema & Admin:*\n"
        "/status — Uso de tokens e mensagens\n"
        "/status\\_server — Saúde do hardware/servidor\n"
        "/modelo — Trocar modelo IA (Backup: Flash Lite, Gemma)\n"
        "/update — Atualizar bot via GitHub\n"
        "/logs — Ver logs recentes do serviço\n\n"
        "🧠 *Memória & Personas:*\n"
        "/persona — Menu de troca de personalidade\n"
        "/memoria — Ver contexto atual do chat\n"
        "/memoria\\_limpar — Resetar histórico local\n"
        "/henricovisky, /mestre, /dev, /financeiro, /curto (Atalhos)\n\n"
        "📝 *Produtividade:*\n"
        "/nota <texto> — Salvar nota rápida\n"
        "/notas — Listar suas notas salvas\n"
        "/nota\\_apagar <id> — Remover uma nota\n"
        "/task add <texto> — Adicionar tarefa\n"
        "/task list — Ver tarefas pendentes\n"
        "/task done <id> — Concluir tarefa\n"
        "/briefing — Resumo inteligente do seu dia\n\n"
        "🌐 *Infraestrutura:*\n"
        "/server — Menu de gestão do servidor e Tailscale\n"
        "/logs — Ver logs recentes do sistema\n\n"
        "🎲 *Módulo RPG:*\n"
        "/rpg\\_transcrever — Processar áudio do Drive\n"
        "/rpg\\_resumo — Gerar PDF épico da sessão"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    relatorio = token_manager.relatorio_hoje()
    n_msgs = conversation_service.count_messages(chat_id)
    await update.message.reply_text(
        f"📊 *Status do Agente*\n\n"
        f"*Tokens hoje:*\n{relatorio}\n\n"
        f"*Mensagens na conversa atual:* {n_msgs}",
        parse_mode="Markdown",
    )


async def status_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # CPU
    cpu_pct = psutil.cpu_percent(interval=0.5)
    cpu_count = psutil.cpu_count(logical=True)
    cpu_freq = psutil.cpu_freq()

    # RAM
    ram = psutil.virtual_memory()
    ram_used = _fmt_bytes(ram.used)
    ram_total = _fmt_bytes(ram.total)

    # Disco (raiz do sistema)
    disk = psutil.disk_usage("/")
    disk_used = _fmt_bytes(disk.used)
    disk_total = _fmt_bytes(disk.total)

    # Rede (IPs locais)
    ips = []
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == 2:  # AF_INET
                if not addr.address.startswith("127."):
                    ips.append(f"{interface}: `{addr.address}`")
    ips_str = "\n".join(ips) if ips else "Nenhum IP local encontrado"

    # Uptime do sistema operacional
    sys_uptime = time.time() - psutil.boot_time()
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")

    # Uptime do bot (processo atual)
    bot_uptime = time.time() - _BOT_START

    # Processo Python atual (RAM do bot)
    proc = psutil.Process(os.getpid())
    bot_ram = _fmt_bytes(proc.memory_info().rss)

    # Info do Sistema (OS, Kernel)
    import platform
    os_name = platform.system()
    os_release = platform.release()
    os_version = platform.version()
    
    distro_str = ""
    if os_name == "Linux":
        try:
            with open("/etc/os-release") as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith("PRETTY_NAME="):
                        distro_str = line.split("=")[1].strip().replace('"', '')
                        break
        except:
            distro_str = "Linux (distro desconhecida)"
    else:
        distro_str = f"{os_name} {os_release}"

    # Load average (Linux) ou CPU percent (Windows)
    try:
        load = os.getloadavg()
        load_str = f"{load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}"
    except AttributeError:
        load_str = f"{cpu_pct}% (Windows — sem load avg)"

    msg = (
        "🖥️ *Status do Servidor*\n\n"
        f"🐧 *Sistema:* `{distro_str}`\n"
        f"🏗 *Kernel:* `{os_release}`\n"
        f"🗓 *Boot:* `{boot_time}`\n"
        f"⏱ *Uptime SO:* `{_fmt_uptime(sys_uptime)}`\n"
        f"🤖 *Uptime Bot:* `{_fmt_uptime(bot_uptime)}`\n\n"
        f"🧠 *CPU:* `{cpu_pct}%` ({cpu_count} cores @ {cpu_freq.current if cpu_freq else 'N/A'}MHz)\n"
        f"📈 *Load avg (1/5/15m):* `{load_str}`\n\n"
        f"💾 *RAM total:* `{ram_total}`\n"
        f"   Usada: `{ram_used}` ({ram.percent}%)\n"
        f"   Bot:   `{bot_ram}`\n\n"
        f"💿 *Disco (/):* `{disk_used}` / `{disk_total}` ({disk.percent}%)\n\n"
        f"🌐 *Rede (IPs):*\n{ips_str}"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


async def memoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    hist = conversation_service.get_history_string(chat_id)
    if not hist:
        await update.message.reply_text("Sem histórico guardado.")
        return
    await update.message.reply_text(
        f"🧠 *Contexto atual:*\n\n{hist[:3800]}",
        parse_mode="Markdown",
    )


async def memoria_limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conversation_service.reset_conversation(update.effective_chat.id)
    await update.message.reply_text("✅ Histórico apagado. Nova conversa iniciada.")
