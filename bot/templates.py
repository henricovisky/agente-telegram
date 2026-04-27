"""
Central de templates visuais para o Oráculo.
Define a estética das mensagens de retorno para o módulo de Produtividade Pessoal.
"""

from datetime import datetime

class ProductivityTemplates:
    
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
        
        lista = "\n".join([f"└ 🔘 {t}" for t in list_preview])
        return f"{header}{lista}\n\n"

    @staticmethod
    def section_notes_briefing(notes_preview: list[str]) -> str:
        if not notes_preview:
            return ""
        header = "📌 *Notas Recentes:*\n"
        lista = "\n".join([f"└ 📝 {n}" for n in notes_preview])
        return f"{header}{lista}\n\n"

    @staticmethod
    def reminder_scheduled(time_str: str, text: str) -> str:
        return (
            "🔔 *Lembrete Agendado!*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ *Quando:* `{time_str}`\n"
            f"📝 *O quê:* {text}\n"
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
            # Limpa caracteres que quebram o markdown e trunca
            clean_text = n['text'].replace("*", "").replace("_", "").replace("`", "")
            txt = clean_text[:50] + "..." if len(clean_text) > 50 else clean_text
            lista.append(f"`#{n['id']}` — {txt}")
            
        return header + "\n".join(lista) + "\n\n_Dica: Use `/nota_apagar ID` para remover._"

    @staticmethod
    def task_added(task: str) -> str:
        return f"➕ *Tarefa adicionada:* {task}"

    @staticmethod
    def email_list(emails: list[dict]) -> str:
        if not emails:
            return "📧 *E-mails:* Sua caixa de entrada está limpa! ✨"
        
        header = "📧 *E-mails Recentes (Não Lidos)*\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        lista = []
        for e in emails:
            from_name = e['from'].split('<')[0].strip()
            lista.append(f"👤 *{from_name}*\n└ ✉️ {e['subject']}\n   _Resumo: {e['summary']}_")
            
        return header + "\n\n".join(lista)
