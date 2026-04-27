import os
import asyncio
import re
import edge_tts
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from config import logger

class OutputHandler:
    """
    Implementa as estratégias de saída (Output) conforme telegram-output.md.
    Responsável por: Smart Chunking, TTS (Edge-TTS) e envio de arquivos.
    """
    
    TEMP_DIR = "tmp"
    VOICE_ID = "pt-BR-ThalitaMultilingualNeural"

    def __init__(self):
        if not os.path.exists(self.TEMP_DIR):
            os.makedirs(self.TEMP_DIR)

    async def send_output(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, requires_audio: bool = False):
        """
        Método central para envio de respostas.
        Analisa o texto em busca de blocos de arquivo antes de enviar o restante.
        """
        chat_id = update.effective_chat.id

        # 1. Processa e remove blocos de arquivos [FILE: name.ext]...[/FILE]
        text_restante, files_found = self._extract_files(text)
        
        for filename, content in files_found:
            await self._send_file(update, context, filename, content)

        # 2. Envia o texto restante (Áudio ou Texto)
        if not text_restante.strip() and files_found:
            return

        if requires_audio:
            success = await self._send_audio(update, context, text_restante)
            if not success:
                await self._send_text(update, context, text_restante)
        else:
            await self._send_text(update, context, text_restante)

    async def _send_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """
        TextOutputStrategy: Smart Chunking para mensagens > 4096 caracteres.
        """
        if not text.strip():
            return

        chunks = self._smart_split(text)
        for chunk in chunks:
            try:
                await update.message.reply_text(chunk, parse_mode='Markdown')
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Erro ao enviar chunk de texto: {e}")
                # Fallback sem Markdown
                await update.message.reply_text(chunk)

    async def _send_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
        """
        AudioOutputStrategy: Converte texto em voz e envia como Voice Note.
        """
        chat_id = update.effective_chat.id
        # Limpa o texto de marcações Markdown pesadas para o TTS
        clean_text = re.sub(r'[*_`#\-\[\]()]', '', text)
        
        temp_audio = os.path.join(self.TEMP_DIR, f"voice_{chat_id}_{int(asyncio.get_event_loop().time())}.ogg")
        
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)
            
            communicate = edge_tts.Communicate(clean_text, self.VOICE_ID)
            await communicate.save(temp_audio)
            
            with open(temp_audio, 'rb') as voice:
                await update.message.reply_voice(voice=voice, caption="🎙️ Resposta em áudio")
            
            return True
        except Exception as e:
            logger.error(f"Erro na AudioOutputStrategy: {e}")
            return False
        finally:
            if os.path.exists(temp_audio):
                os.remove(temp_audio)

    async def _send_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, filename: str, content: str):
        """
        FileOutputStrategy: Envia um conteúdo como arquivo anexo.
        """
        temp_file = os.path.join(self.TEMP_DIR, filename)
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            with open(temp_file, 'rb') as f:
                await update.message.reply_document(document=f, filename=filename, caption=f"📄 Gerado: {filename}")
        except Exception as e:
            logger.error(f"Erro ao enviar arquivo {filename}: {e}")
            await update.message.reply_text(f"⚠️ Erro ao gerar arquivo {filename}. Enviando como texto abaixo:")
            await self._send_text(update, context, content)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def _extract_files(self, text: str) -> tuple[str, list[tuple[str, str]]]:
        """
        Busca por padrões [FILE: nome.md]...[/FILE] no texto.
        Retorna (texto_limpo, lista_de_arquivos).
        """
        pattern = r"\[FILE:\s*(.*?)\](.*?)\[/FILE\]"
        files = re.findall(pattern, text, re.DOTALL)
        clean_text = re.sub(pattern, "", text, flags=re.DOTALL).strip()
        
        # Limpa espaços extras no conteúdo dos arquivos
        files_cleaned = [(name.strip(), content.strip()) for name, content in files]
        return clean_text, files_cleaned

    def _smart_split(self, text: str, limit: int = 4000) -> list[str]:
        """
        Divide o texto em blocos respeitando parágrafos e limites do Telegram.
        """
        if len(text) <= limit:
            return [text]

        chunks = []
        current_chunk = ""
        
        paragraphs = text.split('\n')
        
        for p in paragraphs:
            if len(current_chunk) + len(p) + 1 <= limit:
                current_chunk += p + '\n'
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                if len(p) > limit:
                    # Se o parágrafo sozinho for gigante, quebra bruto
                    for i in range(0, len(p), limit):
                        chunks.append(p[i:i+limit])
                else:
                    current_chunk = p + '\n'
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks

# Instância global
output_handler = OutputHandler()
