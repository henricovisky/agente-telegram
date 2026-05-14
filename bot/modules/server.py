"""
Módulo de Gestão de Infraestrutura e Servidor.
Permite monitorar a rede Tailscale, serviços e recursos do sistema
via comandos diretos ou via painel de botões Inline.
"""
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.terminal_service import terminal_service

# ---------------------------------------------------------------------------
# Comandos pré-definidos do arsenal tático
# ---------------------------------------------------------------------------
TACTICAL_COMMANDS = {
    # Saúde e Memória
    "srv:uptime":    ("⚡ Carga & RAM",     "uptime && echo '' && free -h"),
    "srv:procs":     ("🧠 Top Processos",   "ps -eo pid,user,%mem,%cpu,comm --sort=-%mem | head -n 11"),
    "srv:disk":      ("💾 Disco /",          "df -h /"),
    # Serviços e Logs
    "srv:status":    ("⚙️ Status do Bot",   "systemctl status henricovisky --no-pager -l"),
    "srv:logs":      ("📋 Logs (15 linhas)","journalctl -u henricovisky -n 15 --no-pager"),
    "srv:logins":    ("👤 Últimos Logins",  "last -a | head -n 7"),
    # Rede
    "srv:net":       ("🌐 Tailscale",       "tailscale status"),
    "srv:ports":     ("🔌 Portas Abertas",  "ss -tuln"),
    # Faxina (avançados)
    "srv:dropcache": ("🧹 Limpar Cache RAM","sudo sync && sudo sysctl -w vm.drop_caches=3"),
    "srv:dudata":    ("📦 Tamanho /data",   "du -sh /opt/henricovisky/data/ 2>/dev/null || du -sh ~/data/ 2>/dev/null || echo 'Pasta não encontrada'"),
}

# Agrupamento para o teclado inline (linhas do painel)
KEYBOARD_LAYOUT = [
    # Linha 1 — Saúde
    ["srv:uptime", "srv:procs", "srv:disk"],
    # Linha 2 — Serviço
    ["srv:status", "srv:logs", "srv:logins"],
    # Linha 3 — Rede
    ["srv:net", "srv:ports"],
    # Linha 4 — Avançado
    ["srv:dropcache", "srv:dudata"],
]


def _build_keyboard() -> InlineKeyboardMarkup:
    """Constrói o teclado inline do painel de servidor."""
    buttons = []
    for row_keys in KEYBOARD_LAYOUT:
        row = []
        for key in row_keys:
            label, _ = TACTICAL_COMMANDS[key]
            row.append(InlineKeyboardButton(label, callback_data=key))
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def _panel_text() -> str:
    return (
        "🖥️ *Painel de Gestão — Jarvis*\n\n"
        "Selecione uma ação ou use os subcomandos:\n"
        "• `/server exec [cmd]` — Comando livre\n"
        "• `/server rules` — Diretrizes de gestão\n\n"
        "_Dica: use comandos one-shot para evitar travamentos._"
    )


# ---------------------------------------------------------------------------
# Handler principal
# ---------------------------------------------------------------------------
async def server_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler principal para comandos de servidor."""
    args = context.args
    command_name = update.message.text.split()[0][1:]

    # /skill_servidor → abre as diretrizes
    if command_name == "skill_servidor":
        await _send_rules(update)
        return

    # Sem argumentos → mostra o painel com botões
    if not args:
        await update.message.reply_text(
            _panel_text(),
            parse_mode="Markdown",
            reply_markup=_build_keyboard(),
        )
        return

    subcmd = args[0].lower()

    if subcmd == "rules":
        await _send_rules(update)

    elif subcmd == "net":
        await update.message.reply_chat_action("typing")
        res = terminal_service.execute("tailscale status")
        await update.message.reply_text(f"🌐 *Tailscale Status:*\n\n`{res}`", parse_mode="Markdown")

    elif subcmd == "service":
        await update.message.reply_chat_action("typing")
        res = terminal_service.execute("systemctl status henricovisky --no-pager -l")
        await update.message.reply_text(f"⚙️ *Service Status:*\n\n`{res}`", parse_mode="Markdown")

    elif subcmd == "restart":
        await update.message.reply_text("🔄 Reiniciando serviço… (o bot pode cair brevemente)")
        terminal_service.execute("sudo systemctl restart henricovisky")

    elif subcmd == "exec":
        cmd = " ".join(args[1:])
        if not cmd:
            await update.message.reply_text("❌ Informe o comando: `/server exec <comando>`", parse_mode="Markdown")
            return
        await update.message.reply_chat_action("typing")
        res = terminal_service.execute(cmd)
        await _send_terminal_output(update, cmd, res)

    else:
        await update.message.reply_text(
            "❌ Subcomando desconhecido.\n\nUse `/server` para ver o painel.",
            parse_mode="Markdown",
        )


# ---------------------------------------------------------------------------
# Callback dos botões inline
# ---------------------------------------------------------------------------
async def server_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa cliques nos botões do painel de servidor."""
    query = update.callback_query
    await query.answer()

    key = query.data
    if key not in TACTICAL_COMMANDS:
        await query.edit_message_text("❌ Ação desconhecida.")
        return

    label, cmd = TACTICAL_COMMANDS[key]

    # Atualiza a mensagem para mostrar que está processando
    await query.edit_message_text(
        f"⏳ Executando: *{label}*…",
        parse_mode="Markdown",
    )

    res = terminal_service.execute(cmd)

    # Formata a saída — trunca se necessário
    output = res if res else "_(sem saída)_"
    if len(output) > 3800:
        output = output[:3800] + "\n… *(truncado)*"

    reply_text = f"*{label}*\n`$ {cmd}`\n\n```\n{output}\n```"

    # Restaura o painel com os botões após a execução
    await query.edit_message_text(
        reply_text,
        parse_mode="Markdown",
    )

    # Envia o painel novamente como nova mensagem para facilitar próximas ações
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=_panel_text(),
        parse_mode="Markdown",
        reply_markup=_build_keyboard(),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _send_rules(update: Update):
    path = "docs/skills/server_management.md"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 4000:
            content = content[:4000] + "\n… *(truncado)*"
        await update.message.reply_text(
            f"📜 *Diretrizes de Servidor:*\n\n{content}",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("❌ Arquivo `docs/skills/server_management.md` não encontrado.")


async def _send_terminal_output(update: Update, cmd: str, res: str):
    """Envia saída formatada de um comando livre."""
    if len(res) > 3800:
        res = res[:3800] + "\n… *(truncado)*"
    await update.message.reply_text(
        f"💻 *Terminal*\n`$ {cmd}`\n\n```\n{res}\n```",
        parse_mode="Markdown",
    )
