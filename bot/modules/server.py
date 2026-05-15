"""
Módulo de Gestão de Infraestrutura e Servidor.

Painel central de infra: exibe botões inline para todos os comandos táticos.
Absorve as funções de /logs e /status_server, que viram aliases para cá.
"""
import os
import html
import time
import datetime
import platform
import psutil

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import logger
from services.terminal_service import terminal_service

# ---------------------------------------------------------------------------
# Arsenal tático: { callback_data: (label_botão, comando_shell | None) }
# None = handler Python interno (veja _PYTHON_HANDLERS)
# ---------------------------------------------------------------------------
TACTICAL_COMMANDS = {
    # --- Saúde e Memória ---
    "srv:uptime":    ("⚡ Carga & RAM",      "uptime && echo '' && free -h"),
    "srv:procs":     ("🧠 Top Processos",    "ps -eo pid,user,%mem,%cpu,comm --sort=-%mem | head -n 11"),
    "srv:disk":      ("💾 Disco /",           "df -h /"),
    "srv:sysinfo":   ("🖥️ Sys Info",          None),   # handler Python (psutil)
    # --- Serviço e Logs ---
    "srv:status":    ("⚙️ Status do Bot",    "systemctl status henricovisky --no-pager -l"),
    "srv:logs":      ("📋 Logs (20 linhas)", "journalctl -u henricovisky -n 20 --no-pager"),
    "srv:logins":    ("👤 Últimos Logins",   "last -a | head -n 7"),
    "srv:restart":   ("🔄 Restart Bot",       None),   # handler Python (reinicia serviço)
    # --- Rede ---
    "srv:net":       ("🌐 Tailscale",        "tailscale status"),
    "srv:ports":     ("🔌 Portas Abertas",   "ss -tuln"),
    # --- Faxina / Avançado ---
    "srv:dropcache": ("🧹 Limpar Cache RAM", "sudo sync && sudo sysctl -w vm.drop_caches=3"),
    "srv:dudata":    ("📦 Tamanho /data",    "du -sh /opt/henricovisky/data/ 2>/dev/null || echo 'Pasta não encontrada'"),
}

# Layout do teclado — cada sub-lista = uma linha de botões
KEYBOARD_LAYOUT = [
    ["srv:uptime",  "srv:procs",  "srv:disk"],
    ["srv:sysinfo"],
    ["srv:status",  "srv:logs",   "srv:logins"],
    ["srv:restart"],
    ["srv:net",     "srv:ports"],
    ["srv:dropcache", "srv:dudata"],
]

PANEL_TEXT = (
    "🖥️ <b>Painel de Gestão — Jarvis</b>\n\n"
    "Toque em um botão para executar o comando no servidor.\n\n"
    "<i>Para comandos avulsos: </i><code>/server exec &lt;comando&gt;</code>"
)


# ---------------------------------------------------------------------------
# Helpers visuais
# ---------------------------------------------------------------------------

def _build_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for row_keys in KEYBOARD_LAYOUT:
        row = [
            InlineKeyboardButton(TACTICAL_COMMANDS[k][0], callback_data=k)
            for k in row_keys
            if k in TACTICAL_COMMANDS
        ]
        if row:
            rows.append(row)
    return InlineKeyboardMarkup(rows)


def _format_shell_output(label: str, cmd: str, output: str) -> str:
    safe_out = html.escape(output)
    safe_cmd = html.escape(cmd)
    if len(safe_out) > 3500:
        safe_out = safe_out[:3500] + "\n… (truncado)"
    return f"<b>{label}</b>\n<code>$ {safe_cmd}</code>\n\n<pre>{safe_out}</pre>"


def _format_python_output(label: str, output: str) -> str:
    safe_out = html.escape(output)
    if len(safe_out) > 3500:
        safe_out = safe_out[:3500] + "\n… (truncado)"
    return f"<b>{label}</b>\n\n<pre>{safe_out}</pre>"


# ---------------------------------------------------------------------------
# Handlers Python internos (não usam shell)
# ---------------------------------------------------------------------------

def _run_sysinfo() -> str:
    """Gera relatório de hardware via psutil (igual ao antigo /status_server)."""
    def fmt_bytes(n):
        for u in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.1f} {u}"
            n /= 1024
        return f"{n:.1f} TB"

    def fmt_uptime(s):
        d = datetime.timedelta(seconds=int(s))
        parts = []
        if d.days:
            parts.append(f"{d.days}d")
        h, rem = divmod(d.seconds, 3600)
        m, s2 = divmod(rem, 60)
        if h:
            parts.append(f"{h}h")
        parts.append(f"{m}m {s2}s")
        return " ".join(parts)

    cpu_pct   = psutil.cpu_percent(interval=0.5)
    cpu_count = psutil.cpu_count(logical=True)
    cpu_freq  = psutil.cpu_freq()
    ram       = psutil.virtual_memory()
    disk      = psutil.disk_usage("/")
    sys_up    = time.time() - psutil.boot_time()
    boot_dt   = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M")

    try:
        load = os.getloadavg()
        load_str = f"{load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}"
    except AttributeError:
        load_str = f"{cpu_pct}% (sem load avg)"

    os_name = platform.system()
    distro  = os_name
    if os_name == "Linux":
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        distro = line.split("=", 1)[1].strip().strip('"')
                        break
        except Exception:
            pass

    ips = []
    for iface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == 2 and not addr.address.startswith("127."):
                ips.append(f"  {iface}: {addr.address}")

    lines = [
        f"OS:      {distro}",
        f"Kernel:  {platform.release()}",
        f"Boot:    {boot_dt}",
        f"Uptime:  {fmt_uptime(sys_up)}",
        "",
        f"CPU:     {cpu_pct}% ({cpu_count} cores @ {cpu_freq.current if cpu_freq else 'N/A'} MHz)",
        f"Load:    {load_str}",
        "",
        f"RAM:     {fmt_bytes(ram.used)} / {fmt_bytes(ram.total)} ({ram.percent}%)",
        f"Disco:   {fmt_bytes(disk.used)} / {fmt_bytes(disk.total)} ({disk.percent}%)",
    ]
    if ips:
        lines += ["", "IPs:"] + ips

    return "\n".join(lines)


async def _run_restart(context, chat_id: int) -> str:
    """Agenda reinício via systemd e retorna mensagem de status."""
    res = terminal_service.execute("sudo systemctl restart henricovisky")
    return res or "Comando de restart enviado. O bot pode cair brevemente."


# ---------------------------------------------------------------------------
# Handler: /server [subcomando]
# ---------------------------------------------------------------------------

async def server_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe o painel de botões ou executa subcomandos diretos."""
    args = context.args or []

    if not args:
        await update.message.reply_text(
            PANEL_TEXT,
            parse_mode="HTML",
            reply_markup=_build_keyboard(),
        )
        return

    subcmd = args[0].lower()

    if subcmd == "exec":
        cmd = " ".join(args[1:]).strip()
        if not cmd:
            await update.message.reply_text(
                "❌ Informe o comando:\n<code>/server exec &lt;comando&gt;</code>",
                parse_mode="HTML",
            )
            return
        await update.message.reply_chat_action("typing")
        res = terminal_service.execute(cmd)
        await update.message.reply_text(
            _format_shell_output("💻 Terminal", cmd, res),
            parse_mode="HTML",
        )

    elif subcmd == "restart":
        await update.message.reply_text("🔄 Reiniciando serviço… (o bot pode cair brevemente)")
        terminal_service.execute("sudo systemctl restart henricovisky")

    elif subcmd == "rules":
        await _send_rules(update)

    else:
        await update.message.reply_text(
            f"❓ Subcomando <code>{html.escape(subcmd)}</code> desconhecido.\n\n" + PANEL_TEXT,
            parse_mode="HTML",
            reply_markup=_build_keyboard(),
        )


# ---------------------------------------------------------------------------
# Alias: /logs e /status_server abrem o painel diretamente
# ---------------------------------------------------------------------------

async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/logs — exibe o painel e roda logs imediatamente."""
    await update.message.reply_chat_action("typing")
    # Executa o comando de logs direto e exibe resultado com painel
    label, cmd = TACTICAL_COMMANDS["srv:logs"]
    res = terminal_service.execute(cmd)
    await update.message.reply_text(
        _format_shell_output(label, cmd, res),
        parse_mode="HTML",
        reply_markup=_build_keyboard(),
    )


async def status_server_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/status_server — exibe sys info e abre o painel."""
    await update.message.reply_chat_action("typing")
    output = _run_sysinfo()
    await update.message.reply_text(
        _format_python_output("🖥️ Sys Info", output),
        parse_mode="HTML",
        reply_markup=_build_keyboard(),
    )


# ---------------------------------------------------------------------------
# Callback: clique nos botões do painel
# ---------------------------------------------------------------------------

async def server_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa o clique em um botão inline do painel de servidor."""
    query = update.callback_query
    await query.answer()

    key = query.data
    if key not in TACTICAL_COMMANDS:
        await query.edit_message_text("❌ Ação desconhecida.")
        return

    label, cmd = TACTICAL_COMMANDS[key]

    # Feedback imediato
    try:
        await query.edit_message_text(
            f"⏳ Executando: <b>{html.escape(label)}</b>…",
            parse_mode="HTML",
        )
    except Exception:
        pass

    # Execução: shell ou handler Python
    if cmd is None:
        # Handler Python interno
        if key == "srv:sysinfo":
            result_str = _run_sysinfo()
            result_text = _format_python_output(label, result_str)
        elif key == "srv:restart":
            res = await _run_restart(context, query.message.chat_id)
            result_text = _format_python_output(label, res)
        else:
            result_text = f"<b>{label}</b>\n\n❌ Handler não implementado."
    else:
        res = terminal_service.execute(cmd)
        result_text = _format_shell_output(label, cmd, res)

    # Exibe resultado mantendo os botões
    try:
        await query.edit_message_text(
            result_text,
            parse_mode="HTML",
            reply_markup=_build_keyboard(),
        )
    except Exception as e:
        logger.warning(f"Erro ao editar mensagem do painel: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=result_text,
            parse_mode="HTML",
            reply_markup=_build_keyboard(),
        )


# ---------------------------------------------------------------------------
# Helper: regras / docs
# ---------------------------------------------------------------------------

async def _send_rules(update: Update):
    path = "docs/skills/server_management.md"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 4000:
            content = content[:4000] + "\n… (truncado)"
        await update.message.reply_text(
            f"📜 <b>Diretrizes de Servidor:</b>\n\n{html.escape(content)}",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text("❌ Arquivo de diretrizes não encontrado.")
