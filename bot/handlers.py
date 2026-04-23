import os
from telegram import Update
from telegram.ext import ContextTypes

from config import DRIVE_FOLDER_ID, logger
from services.drive_service import DriveService
from services.gemini_service import GeminiService
from services.pdf_service import PdfService


class BotHandlers:
    """
    Agrupa todos os handlers (controladores) de comandos do bot Telegram.
    Coordena a orquestração dos serviços de Drive, Gemini e PDF,
    comunicando o progresso ao utilizador em cada etapa.
    """

    def __init__(self):
        """
        Inicializa os serviços que serão utilizados pelos handlers.
        As instâncias são partilhadas entre chamadas para evitar
        reconstrução desnecessária de clientes de API.
        """
        self._drive = DriveService()
        self._gemini = GeminiService()
        self._pdf = PdfService()

    async def rpg_transcrever(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handler para o comando /rpg_transcrever.
        Localiza o áudio, transcreve e guarda o TXT no Drive.
        """
        chat_id = update.effective_chat.id
        caminho_audio = None
        caminho_txt = None

        try:
            await context.bot.send_message(chat_id=chat_id, text="🎙️ A iniciar a transcrição... Procura do áudio no Drive...")

            audio_info = await self._drive.encontrar_audio_mais_recente()
            if not audio_info:
                await context.bot.send_message(chat_id=chat_id, text="❌ Nenhum áudio encontrado.")
                return

            file_id = audio_info['id']
            file_name = audio_info['name']
            caminho_audio = f"temp_{file_id}.mp3"

            await context.bot.send_message(chat_id=chat_id, text=f"📥 Baixando '{file_name}'...")
            await self._drive.fazer_download(file_id, caminho_audio)

            await context.bot.send_message(chat_id=chat_id, text="⚙️ Transcrevendo com Gemini (File API)...")
            transcricao = await self._gemini.transcrever_audio(caminho_audio)

            caminho_txt = f"transcricao_{file_id}.txt"
            with open(caminho_txt, "w", encoding="utf-8") as f:
                f.write(transcricao)

            await self._drive.fazer_upload(
                caminho_txt,
                nome=f"Transcricao_{file_name}.txt",
                mime_type="text/plain"
            )

            await context.bot.send_message(chat_id=chat_id, text="✅ Transcrição concluída e enviada ao Drive!")

        except Exception as e:
            logger.error(f"Erro em /rpg_transcrever: {e}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Erro: {str(e)}")
        finally:
            for c in [caminho_audio, caminho_txt]:
                if c and os.path.exists(c): os.remove(c)

    async def rpg_resumo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handler para o comando /rpg_resumo.
        Localiza a transcrição (.txt), gera a crônica e o PDF.
        """
        chat_id = update.effective_chat.id
        caminho_txt = None
        caminho_pdf = None

        try:
            await context.bot.send_message(chat_id=chat_id, text="📜 Procura da transcrição mais recente no Drive...")

            txt_info = await self._drive.encontrar_transcricao_mais_recente()
            if not txt_info:
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text="❌ Nenhuma transcrição (.txt) encontrada. Use /rpg_transcrever primeiro."
                )
                return

            file_id = txt_info['id']
            file_name = txt_info['name']
            caminho_txt = f"temp_txt_{file_id}.txt"

            await context.bot.send_message(chat_id=chat_id, text=f"📥 Baixando transcrição '{file_name}'...")
            await self._drive.fazer_download(file_id, caminho_txt)

            with open(caminho_txt, "r", encoding="utf-8") as f:
                transcricao = f.read()

            await context.bot.send_message(chat_id=chat_id, text="✨ Gerando Crônica Épica (RAG + Gemini)...")
            cronica_md = await self._gemini.gerar_cronica_epica(transcricao)

            caminho_pdf = f"Cronica_{file_id}.pdf"
            await self._pdf.criar_pdf(cronica_md, caminho_pdf)

            await self._drive.fazer_upload(
                caminho_pdf,
                nome=f"Cronica_{file_name.replace('.txt', '')}.pdf",
                mime_type="application/pdf"
            )

            with open(caminho_pdf, 'rb') as pdf_file:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=pdf_file,
                    filename=f"Cronica_{file_name.replace('.txt', '')}.pdf"
                )

            await context.bot.send_message(chat_id=chat_id, text="⚔️ Crônica entregue com sucesso!")

        except Exception as e:
            logger.error(f"Erro em /rpg_resumo: {e}", exc_info=True)
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Erro: {str(e)}")
        finally:
            for c in [caminho_txt, caminho_pdf]:
                if c and os.path.exists(c): os.remove(c)

