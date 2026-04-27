"""
Módulo de Gestão de Infraestrutura e Servidor.
Permite monitorar a rede Tailscale e gerenciar serviços do sistema.
"""
from telegram import Update
from telegram.ext import ContextTypes
from services.terminal_service import terminal_service

async def server_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler principal para comandos de servidor."""
    args = context.args
    command_name = update.message.text.split()[0][1:]  # Extrai o nome do comando usado (ex: server, skill_servidor)

    # Se o comando for especificamente para a skill ou se não houver argumentos
    if command_name == "skill_servidor" or not args:
        # Se for /skill_servidor ou /server rules (implícito ou explícito)
        if command_name == "skill_servidor" or (args and args[0].lower() == "rules"):
            import os
            path = "docs/skills/server_management.md"
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                await update.message.reply_text(f"📜 *Diretrizes de Servidor (Skill):*\n\n{content}", parse_mode="Markdown")
                return
        
        # Menu padrão se não houver argumentos no /server ou /servidor
        await update.message.reply_text(
            "🖥️ *Gestão de Servidor*\n\n"
            "• `/server net` — Status da rede Tailscale\n"
            "• `/server service` — Status do serviço do bot\n"
            "• `/server restart` — Reiniciar o bot (systemd)\n"
            "• `/server rules` — Ver diretrizes de gestão\n"
            "• `/server exec [cmd]` — Executar comando livre",
            parse_mode="Markdown"
        )
        return

    subcmd = args[0].lower()
    
    if subcmd == "rules":
        import os
        path = "docs/skills/server_management.md"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            await update.message.reply_text(f"📜 *Diretrizes de Servidor:*\n\n{content}", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Arquivo de diretrizes não encontrado.")
        return

    elif subcmd == "net":
        await update.message.reply_chat_action("typing")
        res = terminal_service.execute("tailscale status")
        await update.message.reply_text(f"🌐 *Tailscale Status:*\n\n`{res}`", parse_mode="Markdown")

    elif subcmd == "service":
        await update.message.reply_chat_action("typing")
        res = terminal_service.execute("systemctl status henricovisky --no-pager")
        await update.message.reply_text(f"⚙️ *Service Status:*\n\n`{res}`", parse_mode="Markdown")

    elif subcmd == "restart":
        await update.message.reply_text("🔄 Reiniciando serviço...")
        terminal_service.execute("sudo systemctl restart henricovisky")
        # Nota: O bot vai cair e voltar, talvez não consiga confirmar o sucesso via Telegram antes de cair
    
    elif subcmd == "exec":
        cmd = " ".join(args[1:])
        if not cmd:
            await update.message.reply_text("❌ Informe o comando para executar.")
            return
        
        await update.message.reply_chat_action("typing")
        res = terminal_service.execute(cmd)
        await update.message.reply_text(f"💻 *Terminal:*\n\n`{res}`", parse_mode="Markdown")

    else:
        await update.message.reply_text("❌ Subcomando desconhecido.")
