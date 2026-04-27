"""
Módulo de Produtividade Pessoal.
Implementa comandos de Notas, Tarefas e Resumo Diário.
"""
from telegram import Update
from telegram.ext import ContextTypes
from services.productivity_service import productivity_service
from bot.templates import ProductivityTemplates as Tpl

async def nota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Salva uma nota rápida."""
    texto = " ".join(context.args)
    if not texto:
        await update.message.reply_text("❌ Use: `/nota [texto da sua nota]`", parse_mode="Markdown")
        return
    
    chat_id = str(update.effective_chat.id)
    # Limpeza básica para evitar quebra de markdown no retorno
    texto_limpo = texto.replace("*", "").replace("_", "").replace("`", "")
    
    note_id = productivity_service.add_note(chat_id, texto_limpo)
    await update.message.reply_text(Tpl.note_saved(note_id), parse_mode="Markdown")

async def notas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista todas as notas."""
    chat_id = str(update.effective_chat.id)
    lista = productivity_service.get_notes(chat_id)
    await update.message.reply_text(Tpl.notes_list(lista), parse_mode="Markdown")

async def nota_apagar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Apaga uma nota pelo ID."""
    if not context.args:
        await update.message.reply_text("❌ Use: `/nota_apagar [ID]`", parse_mode="Markdown")
        return
    
    chat_id = str(update.effective_chat.id)
    try:
        note_id = int(context.args[0])
        if productivity_service.delete_note(chat_id, note_id):
            await update.message.reply_text(f"✅ Nota `#{note_id}` removida.", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Nota não encontrada ou não pertence a você.")
    except ValueError:
        await update.message.reply_text("❌ O ID deve ser um número.")

async def task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gerencia tarefas (add, list, done)."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "📝 *Gerenciador de Tarefas*\n\n"
            "• `/task add [texto]` — Adiciona nova\n"
            "• `/task list` — Lista pendentes\n"
            "• `/task done [ID]` — Marca como concluída",
            parse_mode="Markdown"
        )
        return
    
    subcmd = args[0].lower()
    chat_id = str(update.effective_chat.id)
    
    if subcmd == "add":
        content = " ".join(args[1:])
        if not content:
            await update.message.reply_text("❌ Qual a tarefa?")
            return
        # Limpeza
        content_limpo = content.replace("*", "").replace("_", "").replace("`", "")
        productivity_service.add_task(chat_id, content_limpo)
        await update.message.reply_text(Tpl.task_added(content_limpo), parse_mode="Markdown")
        
    elif subcmd == "list":
        tasks = productivity_service.get_pending_tasks(chat_id)
        preview = [f"`#{t['id']}` {t['text']}" for t in tasks]
        await update.message.reply_text(
            Tpl.section_tasks(len(tasks), preview),
            parse_mode="Markdown"
        )
        
    elif subcmd == "done":
        try:
            t_id = int(args[1])
            if productivity_service.complete_task(chat_id, t_id):
                await update.message.reply_text(f"✅ Tarefa `#{t_id}` concluída! Bom trabalho. 🏆")
            else:
                await update.message.reply_text("❌ Tarefa não encontrada.")
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Informe o ID da tarefa.")

async def briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gera um resumo visual de produtividade."""
    chat_id = str(update.effective_chat.id)
    
    # Simulação de dados externos (clima e agenda)
    weather = Tpl.section_weather("Sua Cidade", 25.0, "parcialmente nublado")
    calendar = Tpl.section_calendar([]) # Futura integração
    
    # Dados reais do banco
    tasks_data = productivity_service.get_pending_tasks(chat_id)
    tasks_preview = [t['text'] for t in tasks_data[:3]]
    tasks_sec = Tpl.section_tasks(len(tasks_data), tasks_preview)
    
    notes_data = productivity_service.get_notes(chat_id)
    notes_preview = [n['text'][:40] for n in notes_data[:3]]
    notes_sec = Tpl.section_notes_briefing(notes_preview)
    
    msg = (
        Tpl.header_briefing() + 
        weather + 
        calendar + 
        tasks_sec + 
        notes_sec + 
        "_Tenha um dia produtivo!_ 🚀"
    )
    
    await update.message.reply_text(msg, parse_mode="Markdown")
