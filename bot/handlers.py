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

    async def rpg_resumo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handler para o comando /rpg_resumo.

        Fluxo completo:
          1. Encontra o áudio mais recente no Google Drive
          2. Faz o download em blocos (sem sobrecarregar a RAM)
          3. Transcreve com Gemini Flash via File API
          4. Guarda e envia a transcrição bruta para o Drive
          5. Gera a Crónica Épica com Gemini Pro
          6. Cria o PDF localmente com fpdf2
          7. Envia o PDF ao utilizador e faz upload para o Drive
          8. Remove todos os ficheiros temporários do disco local
        """
        chat_id = update.effective_chat.id

        # Variáveis dos ficheiros temporários; inicializadas a None
        # para que o bloco `finally` possa apagar apenas os que foram criados
        caminho_audio = None
        caminho_txt = None
        caminho_pdf = None

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="🕵️‍♀️ A iniciar a procura do áudio mais recente no Drive..."
            )

            # --- Etapa 1: Localizar o áudio no Drive ---
            audio_info = await self._drive.encontrar_audio_mais_recente()
            if not audio_info:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Não encontrei nenhum ficheiro de áudio recente no Drive."
                )
                return

            file_id = audio_info['id']
            file_name = audio_info['name']
            caminho_audio = f"temp_{file_id}.mp3"

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📥 Encontrado: '{file_name}'. A descarregar em blocos..."
            )

            # --- Etapa 2: Download do ficheiro em chunks ---
            await self._drive.fazer_download(file_id, caminho_audio)

            await context.bot.send_message(
                chat_id=chat_id,
                text="⚙️ Áudio descarregado. A enviar para o Gemini e aguardar transcrição..."
            )

            # --- Etapa 3: Transcrição via Gemini Flash + File API ---
            transcricao = await self._gemini.transcrever_audio(caminho_audio)

            # --- Etapa 4: Guardar transcrição bruta em TXT e fazer upload para o Drive ---
            caminho_txt = f"transcricao_{file_id}.txt"
            with open(caminho_txt, "w", encoding="utf-8") as f:
                f.write(transcricao)

            await self._drive.fazer_upload(
                caminho_txt,
                nome=f"Transcricao_Bruta_{file_name}.txt",
                mime_type="text/plain"
            )

            await context.bot.send_message(
                chat_id=chat_id,
                text="📜 Transcrição bruta concluída e guardada no Drive. A gerar a Crónica Épica..."
            )

            # --- Etapa 5: Geração da Crónica Épica com Gemini Pro ---
            cronica_md = await self._gemini.gerar_cronica_epica(transcricao)

            # --- Etapa 6: Geração local do PDF ---
            caminho_pdf = f"Cronica_Epica_{file_id}.pdf"
            await self._pdf.criar_pdf(cronica_md, caminho_pdf)

            await context.bot.send_message(
                chat_id=chat_id,
                text="📚 PDF gerado com sucesso! A fazer upload para o Drive e a enviar para si..."
            )

            # --- Etapa 7: Upload do PDF para o Drive e envio ao utilizador ---
            await self._drive.fazer_upload(
                caminho_pdf,
                nome=f"Cronica_{file_name}.pdf",
                mime_type="application/pdf"
            )

            with open(caminho_pdf, 'rb') as pdf_file:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=pdf_file,
                    filename=f"Cronica_{file_name}.pdf"
                )

            await context.bot.send_message(
                chat_id=chat_id,
                text="✨ Missão cumprida! A Crónica Épica foi entregue."
            )

        except Exception as e:
            logger.error(f"Erro ao processar o comando /rpg_resumo: {e}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Ocorreu um erro inesperado: {str(e)}"
            )

        finally:
            # --- Etapa 8: Limpeza dos ficheiros temporários do disco ---
            logger.info("A apagar ficheiros temporários do disco...")
            for caminho in [caminho_audio, caminho_txt, caminho_pdf]:
                if caminho and os.path.exists(caminho):
                    try:
                        os.remove(caminho)
                        logger.info(f"Ficheiro temporário apagado: {caminho}")
                    except OSError as e:
                        logger.warning(f"Não foi possível apagar '{caminho}': {e}")
