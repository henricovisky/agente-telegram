"""
Central de templates visuais para o Oráculo.
Define a estética das mensagens de retorno para o módulo de Produtividade Pessoal.
"""

from datetime import datetime

class ProductivityTemplates:
    
    @staticmethod
    def _clean_markdown(text: str) -> str:
        """Limpa caracteres que quebram o Markdown V1 do Telegram."""
        if not text: return ""
        return text.replace("*", "").replace("_", "").replace("`", "").replace("[", "(").replace("]", ")")

    @staticmethod
    def header_briefing() -> str:
        data_str = datetime.now().strftime("%d/%m/%Y")
        return (
            f"🌅 *Briefing Matinal — {data_str}*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )

    @staticmethod
    def section_weather(city: str, temp: float, desc: str) -> str:
        return (
            f"☁️ *Clima em {city}:*\n"
            f"└ {temp}°C — {desc.capitalize()}\n\n"
        )

    @staticmethod
    def section_calendar(events: list[str]) -> str:
        if not events:
            return "📅 *Agenda:* Nenhuma reunião hoje. Relaxa! 🙌\n\n"
        
        lista = "\n".join([f"└ 🕒 {e}" for e in events])
        return f"📅 *Agenda:* Você tem {len(events)} compromisso(s):\n{lista}\n\n"

    @staticmethod
    def section_tasks(pending: int, list_preview: list[str]) -> str:
        status = "✅ Tudo em dia!" if pending == 0 else f"⚠️ {pending} pendentes"
        header = f"✅ *Tarefas:* {status}\n"
        if not list_preview:
            return header + "\n"
        
        # Limpa cada tarefa
        lista = "\n".join([f"└ 🔘 {ProductivityTemplates._clean_markdown(t)}" for t in list_preview])
        return f"{header}{lista}\n\n"

    @staticmethod
    def section_notes_briefing(notes_preview: list[str]) -> str:
        if not notes_preview:
            return ""
        header = "📌 *Notas Recentes:*\n"
        # Limpa cada nota
        lista = "\n".join([f"└ 📝 {ProductivityTemplates._clean_markdown(n)}" for n in notes_preview])
        return f"{header}{lista}\n\n"

    @staticmethod
    def reminder_scheduled(time_str: str, text: str) -> str:
        clean_text = ProductivityTemplates._clean_markdown(text)
        return (
            "🔔 *Lembrete Agendado!*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ *Quando:* `{time_str}`\n"
            f"📝 *O quê:* {clean_text}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "_Eu te avisarei assim que chegar a hora._"
        )

    @staticmethod
    def note_saved(note_id: int) -> str:
        return f"📌 *Nota #{note_id} salva com sucesso!*"

    @staticmethod
    def notes_list(notes: list[dict]) -> str:
        if not notes:
            return "📑 *Notas:* Você ainda não salvou nenhuma nota rápida."
        
        header = "📑 *Suas Notas Rápidas*\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        lista = []
        for n in notes:
            clean_text = ProductivityTemplates._clean_markdown(n['text'])
            txt = clean_text[:50] + "..." if len(clean_text) > 50 else clean_text
            lista.append(f"`#{n['id']}` — {txt}")
            
        return header + "\n".join(lista) + "\n\n_Dica: Use `/nota_apagar ID` para remover._"

    @staticmethod
    def task_added(task: str) -> str:
        clean_task = ProductivityTemplates._clean_markdown(task)
        return f"➕ *Tarefa adicionada:* {clean_task}"

    @staticmethod
    def email_list(emails: list[dict]) -> str:
        # ... (mantendo lógica de e-mail se existir)
        if not emails:
            return "📧 *E-mails:* Sua caixa de entrada está limpa! ✨"
        
        header = "📧 *E-mails Recentes (Não Lidos)*\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        lista = []
        for e in emails:
            from_name = ProductivityTemplates._clean_markdown(e['from'].split('<')[0].strip())
            subject = ProductivityTemplates._clean_markdown(e['subject'])
            summary = ProductivityTemplates._clean_markdown(e['summary'])
            lista.append(f"👤 *{from_name}*\n└ ✉️ {subject}\n   _Resumo: {summary}_")
            
        return header + "\n\n".join(lista)
