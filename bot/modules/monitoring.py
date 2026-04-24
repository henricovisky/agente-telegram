import os
import subprocess
import psutil
import re
from telegram import Update
from telegram.ext import ContextTypes
from config import logger, ALLOWED_CHAT_IDS

# Limiares para alertas (percentuais)
CPU_THRESHOLD = 90.0
RAM_THRESHOLD = 90.0
DISK_THRESHOLD = 90.0

# Estado anterior para evitar spam de alertas
_ultima_alerta = {
    "cpu": False,
    "ram": False,
    "disk": False,
    "service_bot": False
}

async def monitoramento_job(context: ContextTypes.DEFAULT_TYPE):
    """Job periódico para monitorar CPU, RAM e Disco e enviar alertas."""
    global _ultima_alerta
    
    # 1. CPU
    cpu = psutil.cpu_percent(interval=1)
    if cpu > CPU_THRESHOLD:
        if not _ultima_alerta["cpu"]:
            await _enviar_alerta(context, f"⚠️ *Alerta de CPU:* Uso em `{cpu}%`!")
            _ultima_alerta["cpu"] = True
    else:
        _ultima_alerta["cpu"] = False

    # 2. RAM
    ram = psutil.virtual_memory().percent
    if ram > RAM_THRESHOLD:
        if not _ultima_alerta["ram"]:
            await _enviar_alerta(context, f"⚠️ *Alerta de RAM:* Uso em `{ram}%`!")
            _ultima_alerta["ram"] = True
    else:
        _ultima_alerta["ram"] = False

    # 3. Disco
    disk = psutil.disk_usage("/").percent
    if disk > DISK_THRESHOLD:
        if not _ultima_alerta["disk"]:
            await _enviar_alerta(context, f"⚠️ *Alerta de Disco:* Uso em `{disk}%`!")
            _ultima_alerta["disk"] = True
    else:
        _ultima_alerta["disk"] = False

    # 4. Verificar status do serviço systemd do bot
    # Se o bot está rodando este código, o serviço está "running", 
    # mas podemos verificar se o systemd o considera "active (running)".
    service_status = _get_service_status("henricovisky")
    if "active (running)" not in service_status.lower():
        if not _ultima_alerta["service_bot"]:
            await _enviar_alerta(context, f"⚠️ *Alerta de Serviço:* O serviço `henricovisky` não está reportando status 'active (running)' via systemd!\n\n`{service_status}`")
            _ultima_alerta["service_bot"] = True
    else:
        _ultima_alerta["service_bot"] = False

async def _enviar_alerta(context: ContextTypes.DEFAULT_TYPE, mensagem: str):
    """Envia mensagem de alerta para todos os chats autorizados."""
    for chat_id in ALLOWED_CHAT_IDS:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚨 *SISTEMA DE MONITORAMENTO*\n\n{mensagem}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Erro ao enviar alerta para {chat_id}: {e}")

def _get_service_status(service_name: str) -> str:
    """Retorna a primeira linha do status do serviço systemd."""
    try:
        cmd = ["systemctl", "status", service_name]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        # Pega as primeiras linhas para ver o status
        lines = result.stdout.splitlines()
        for line in lines:
            if "Active:" in line:
                return line.strip()
        return "Status não encontrado"
    except Exception as e:
        return f"Erro ao obter status: {e}"

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /logs [serviço] - Mostra as últimas 20 linhas de logs do systemd."""
    args = context.args
    service = args[0] if args else "henricovisky"
    
    # Sanitização básica do nome do serviço
    if not re.match(r"^[a-zA-Z0-9\-_]+$", service):
        await update.message.reply_text("❌ Nome de serviço inválido.")
        return

    try:
        # Tenta pegar os logs via journalctl
        cmd = ["journalctl", "-u", service, "-n", "20", "--no-pager"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0:
            output = result.stderr or "Erro desconhecido ao ler logs."
            await update.message.reply_text(f"❌ Erro ao ler logs de `{service}`:\n\n`{output}`", parse_mode="Markdown")
            return

        logs_text = result.stdout
        if not logs_text.strip():
            logs_text = "Nenhum log encontrado para este serviço."

        # Truncar se for muito grande para o Telegram
        if len(logs_text) > 3900:
            logs_text = "..." + logs_text[-3900:]

        await update.message.reply_text(
            f"📋 *Últimos logs de `{service}`:*\n\n```\n{logs_text}\n```",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Erro no comando /logs: {e}")
        await update.message.reply_text(f"❌ Erro interno ao processar logs: {e}")
