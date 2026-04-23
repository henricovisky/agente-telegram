import io
import asyncio
import os
from config import DRIVE_CREDENTIALS_PATH, DRIVE_FOLDER_ID, logger

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from googleapiclient.errors import HttpError


class DriveService:
    """
    Encapsula todas as operações com a API do Google Drive.
    Utiliza OAuth2 (User Account) para autenticação.
    """

    # Escopo de acesso à API do Drive (leitura e escrita)
    SCOPES = ['https://www.googleapis.com/auth/drive']

    def __init__(self, credentials_path: str = DRIVE_CREDENTIALS_PATH, folder_id: str = DRIVE_FOLDER_ID):
        """
        Inicializa o serviço com o caminho para o ficheiro de credenciais
        e o ID da pasta de destino no Drive.
        """
        self._credentials_path = credentials_path
        self._folder_id = folder_id
        self._service = None  # O serviço é construído de forma lazy (apenas quando necessário)

    def _obter_service(self):
        """
        Constrói e devolve o cliente da API do Drive usando OAuth2.
        Verifica se já existe um token; se não, inicia o fluxo de autorização.
        """
        if self._service is None:
            creds = None
            # O ficheiro token.json guarda a autorização para evitar login repetido
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
            
            # Se não há token ou ele expirou, faz o login
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # Carrega as credenciais do cliente (client_secret.json)
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self._credentials_path, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                # Guarda o token para as próximas execuções
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())

            self._service = build('drive', 'v3', credentials=creds)
        return self._service

    async def encontrar_audio_mais_recente(self) -> dict | None:
        """
        Pesquisa na pasta do Drive o ficheiro de áudio mais recente.
        Retorna um dicionário com os metadados do ficheiro ou None se não existir.
        """
        # Monta a query de pesquisa com ou sem filtro de pasta
        if self._folder_id:
            query = f"'{self._folder_id}' in parents and mimeType contains 'audio/' and trashed = false"
        else:
            query = "mimeType contains 'audio/' and trashed = false"

        loop = asyncio.get_running_loop()

        def _pesquisar():
            try:
                service = self._obter_service()
                resultado = service.files().list(
                    q=query,
                    pageSize=1,
                    fields="files(id, name, mimeType, createdTime)",
                    orderBy="createdTime desc"
                ).execute()
                return resultado.get('files', [])
            except HttpError as error:
                if error.resp.status == 404:
                    raise ValueError(
                        f"A pasta com ID '{self._folder_id}' não foi encontrada. "
                        "Verifique se o DRIVE_FOLDER_ID está correto no ficheiro .env "
                        "e se partilhou a pasta com o email da Service Account."
                    )
                raise error

        itens = await loop.run_in_executor(None, _pesquisar)
        return itens[0] if itens else None

    async def fazer_download(self, file_id: str, caminho_local: str) -> str:
        """
        Faz o download de um ficheiro do Drive para o disco local em blocos (chunks) de 1MB,
        evitando carregar o ficheiro completo na memória RAM.
        Retorna o caminho do ficheiro descarregado.
        """
        loop = asyncio.get_running_loop()

        def _download():
            service = self._obter_service()
            request = service.files().get_media(fileId=file_id)
            fh = io.FileIO(caminho_local, 'wb')
            # Tamanho do bloco: 1MB — mantém o consumo de RAM reduzido
            downloader = MediaIoBaseDownload(fh, request, chunksize=1024 * 1024)
            concluido = False
            while not concluido:
                status, concluido = downloader.next_chunk()
                if status:
                    logger.info(f"Download {int(status.progress() * 100)}% concluído.")
            fh.close()

        await loop.run_in_executor(None, _download)
        return caminho_local

    async def fazer_upload(self, caminho_local: str, nome: str, mime_type: str) -> str:
        """
        Faz o upload de um ficheiro local para o Google Drive.
        Retorna o ID do ficheiro criado no Drive.
        """
        loop = asyncio.get_running_loop()

        def _upload():
            service = self._obter_service()
            # Define metadados: nome e pasta destino (se configurada)
            metadados = {'name': nome}
            if self._folder_id:
                metadados['parents'] = [self._folder_id]

            media = MediaFileUpload(caminho_local, mimetype=mime_type, resumable=True)
            ficheiro = service.files().create(
                body=metadados, media_body=media, fields='id'
            ).execute()
            return ficheiro.get('id')

        return await loop.run_in_executor(None, _upload)
