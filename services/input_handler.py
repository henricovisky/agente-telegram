import os
import asyncio
import PyPDF2
from telegram import Update, File
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from services.gemini_service import GeminiService
from config import logger

class InputHandler:
    """
    Implementa o processamento de entradas conforme telegram-input.md.
    Responsável por: Transcrição de áudio, extração de texto de PDF/MD.
    """
    
    TEMP_DIR = "tmp"

    def __init__(self, gemini_service: GeminiService):
        self.gemini = gemini_service
        if not os.path.exists(self.TEMP_DIR):
            os.makedirs(self.TEMP_DIR)

    async def process_voice_or_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> tuple[str, bool]:
        """
        Processa mensagens de voz e áudio.
        Retorna (texto_transcrito, requires_audio_reply=True).
        """
        message = update.message
        voice_or_audio = message.voice or message.audio
        chat_id = update.effective_chat.id

        if not voice_or_audio:
            return "", False

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        
        file_id = voice_or_audio.file_id
        temp_path = os.path.join(self.TEMP_DIR, f"input_{file_id}")
        
        try:
            # Baixa o arquivo
            new_file = await context.bot.get_file(file_id)
            await new_file.download_to_drive(temp_path)
            
            # Transcreve usando Gemini (seguindo a realidade do projeto, mas a lógica do spec)
            transcription = await self.gemini.transcrever_audio(temp_path)
            
            # O spec diz que se o input for áudio, a resposta padrão deve ser áudio (G-05)
            return transcription, True
            
        except Exception as e:
            logger.error(f"Erro ao processar áudio: {e}")
            return "⚠️ Não consegui processar seu áudio.", False
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def process_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """
        Processa documentos PDF e MD.
        Retorna o conteúdo textual do arquivo.
        """
        doc = update.message.document
        if not doc:
            return ""

        file_name = doc.file_name.lower()
        if not (file_name.endswith('.pdf') or file_name.endswith('.md')):
            return "⚠️ Por enquanto só consigo ler arquivos .pdf e .md."

        chat_id = update.effective_chat.id
        file_id = doc.file_id
        temp_path = os.path.join(self.TEMP_DIR, f"doc_{file_id}")

        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            
            new_file = await context.bot.get_file(file_id)
            await new_file.download_to_drive(temp_path)

            content = ""
            if file_name.endswith('.pdf'):
                content = self._extract_pdf_text(temp_path)
            else:
                with open(temp_path, 'r', encoding='utf-8') as f:
                    content = f.read()

            # Adiciona uma legenda informativa
            prefix = f"📄 [Documento: {doc.file_name}]\n\n"
            return prefix + content

        except Exception as e:
            logger.error(f"Erro ao processar documento: {e}")
            return "⚠️ Erro ao ler o documento."
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _extract_pdf_text(self, path: str) -> str:
        """Extrai texto de PDF usando PyPDF2."""
        text = ""
        try:
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"Erro PyPDF2: {e}")
            return "[Erro na extração de texto do PDF]"
        return text

# Instância será criada no chat.py ou centralizada
