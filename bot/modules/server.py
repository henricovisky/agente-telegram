"""
Módulo de Gestão de Infraestrutura e Servidor.
Exibe um painel com botões inline para executar comandos pré-definidos
no servidor Jarvis diretamente pelo Telegram.
"""
import os
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.terminal_service import terminal_service

# ---------------------------------------------------------------------------
# Arsenal tático: { callback_data: (label_botão, comando_shell) }
# ---------------------------------------------------------------------------
TACTICAL_COMMANDS = {
    # --- Saúde e Memória ---
    "srv:uptime":    ("⚡ Carga & RAM",      "uptime && echo '' && free -h"),
    "srv:procs":     ("🧠 Top Processos",    "ps -eo pid,user,%mem,%cpu,comm --sort=-%mem | head -n 11"),
    "srv:disk":      ("💾 Disco /",           "df -h /"),
    # --- Serviço e Logs ---
    "srv:status":    ("⚙️ Status do Bot",    "systemctl status henricovisky --no-pager -l"),
    "srv:logs":      ("📋 Logs (15 linhas)", "journalctl -u henricovisky -n 15 --no-pager"),
    "srv:logins":    ("👤 Últimos Logins",   "last -a | head -n 7"),
    # --- Rede ---
    "srv:net":       ("🌐 Tailscale",        "tailscale status"),
    "srv:ports":     ("🔌 Portas Abertas",   "ss -tuln"),
    # --- Avançado ---
    "srv:dropcache": ("🧹 Limpar Cache RAM", "sudo sync && sudo sysctl -w vm.drop_caches=3"),
    "srv:dudata":    ("📦 Tamanho /data",    "du -sh /opt/henricovisky/data/ 2>/dev/null || echo 'Pasta não encontrada'"),
}

# Layout do teclado: cada lista interna = uma linha de botões
KEYBOARD_LAYOUT = [
    ["srv:uptime", "srv:procs", "srv:disk"],
    ["srv:status", "srv:logs",  "srv:logins"],
    ["srv:net",    "srv:ports"],
    ["srv:dropcache", "srv:dudata"],
]

PANEL_TEXT = (
    "🖥️ <b>Painel de Gestão — Jarvis</b>\n\n"
    "Toque em um botão para executar o comando no servidor.\n\n"
    "<i>Para comandos avulsos use:</i> /server exec &lt;comando&gt;"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_keyboard() -> InlineKeyboardMarkup:
    """Monta o teclado inline a partir do KEYBOARD_LAYOUT."""
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


def _format_output(label: str, cmd: str, output: str) -> str:
    """Formata a saída do comando em HTML para o Telegram."""
    safe_output = html.escape(output)
    safe_cmd    = html.escape(cmd)
    # Trunca saída longa
    if len(safe_output) > 3500:
        safe_output = safe_output[:3500] + "\n… (truncado)"
    return (
        f"<b>{label}</b>\n"
        f"<code>$ {safe_cmd}</code>\n\n"
        f"<pre>{safe_output}</pre>"
    )


# ---------------------------------------------------------------------------
# Handler: /server [subcomando]
# ---------------------------------------------------------------------------

async def server_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe o painel de botões ou executa subcomandos diretos."""
    args = context.args or []

    # /server sem argumentos → painel com botões
    if not args:
        await update.message.reply_text(
            PANEL_TEXT,
            parse_mode="HTML",
            reply_markup=_build_keyboard(),
        )
        return

    subcmd = args[0].lower()

    # --- /server exec <comando livre> ---
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
            _format_output("💻 Terminal", cmd, res),
            parse_mode="HTML",
        )
        return

    # --- /server restart ---
    if subcmd == "restart":
        await update.message.reply_text("🔄 Reiniciando serviço… (o bot pode cair brevemente)")
        terminal_service.execute("sudo systemctl restart henricovisky")
        return

    # --- /server rules ---
    if subcmd == "rules":
        await _send_rules(update)
        return

    # Subcomando desconhecido → mostra o painel
    await update.message.reply_text(
        f"❓ Subcomando <code>{html.escape(subcmd)}</code> desconhecido.\n\n"
        + PANEL_TEXT,
        parse_mode="HTML",
        reply_markup=_build_keyboard(),
    )


# ---------------------------------------------------------------------------
# Callback: clique nos botões do painel
# ---------------------------------------------------------------------------

async def server_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa o clique em um botão inline do painel de servidor."""
    query = update.callback_query
    await query.answer()  # Remove o "relógio" no botão

    key = query.data
    if key not in TACTICAL_COMMANDS:
        await query.edit_message_text("❌ Ação desconhecida.")
        return

    label, cmd = TACTICAL_COMMANDS[key]

    # 1. Feedback imediato: edita a mensagem para mostrar que está rodando
    try:
        await query.edit_message_text(
            f"⏳ Executando: <b>{html.escape(label)}</b>…",
            parse_mode="HTML",
        )
    except Exception:
        pass  # Ignora erro de "mensagem idêntica"

    # 2. Executa o comando
    res = terminal_service.execute(cmd)

    # 3. Mostra o resultado e reexibe o painel com botões
    result_text = _format_output(label, cmd, res)
    try:
        await query.edit_message_text(
            result_text,
            parse_mode="HTML",
            reply_markup=_build_keyboard(),
        )
    except Exception:
        # Se a edição falhar (raro), envia nova mensagem
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=result_text,
            parse_mode="HTML",
            reply_markup=_build_keyboard(),
        )


# ---------------------------------------------------------------------------
# Helper: envia arquivo de diretrizes
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
