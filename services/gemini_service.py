import time
import asyncio
from google import genai
from google.genai import types
from google.genai.errors import APIError

from config import GEMINI_API_KEY, logger


class GeminiService:
    """
    Encapsula todas as operações com a API do Google Gemini.
    Responsável por: upload de arquivos pesados via File API,
    transcrição de áudio e geração da crônica épica de RPG.
    """
    # Modelos atualizados para a nova SDK
    MODELO_TRANSCRICAO = 'gemini-2.5-flash-lite'
    MODELO_CRONICA = 'gemini-2.5-flash'

    # Intervalo de espera base (em segundos)
    INTERVALO_ESPERA_SEGUNDOS = 20
    MAX_RETRIES = 5

    def __init__(self, api_key: str = GEMINI_API_KEY):
        """
        Inicializa o serviço e configura o cliente da nova API do Gemini.
        """
        if not api_key:
            raise ValueError("A GEMINI_API_KEY não foi fornecida. Verifique o arquivo .env.")
        self.client = genai.Client(api_key=api_key)

    async def _executar_com_retry(self, func, *args, **kwargs):
        """
        Executa uma função síncrona com retry em caso de Rate Limit (429).
        Se a API informar o tempo de espera ('retry in Xs'), usa esse tempo + margem.
        Caso contrário, o backoff é exponencial.
        """
        import re
        loop = asyncio.get_running_loop()
        tentativa = 0
        while tentativa < self.MAX_RETRIES:
            try:
                # Executa a função síncrona em uma thread separada para não bloquear o event loop
                return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
            except Exception as e:
                msg = str(e)
                if any(err in msg for err in ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"]):
                    tentativa += 1
                    
                    # Backoff exponencial base
                    espera = float(self.INTERVALO_ESPERA_SEGUNDOS * (2 ** (tentativa - 1)))
                    
                    # Tentar extrair o tempo de espera exato da mensagem (ex: "Please retry in 23.87s")
                    match = re.search(r"retry in ([\d\.]+)s", msg)
                    if match:
                        try:
                            # Adiciona uma margem de segurança de 2 segundos
                            espera = float(match.group(1)) + 2.0
                        except ValueError:
                            pass
                            
                    tipo_erro = "Rate Limit (429)" if "429" in msg else "Service Unavailable (503)"
                    logger.warning(f"{tipo_erro} detectado. Tentativa {tentativa}/{self.MAX_RETRIES}. Aguardando {espera:.1f}s...")
                    
                    if tentativa >= self.MAX_RETRIES:
                        raise RuntimeError(f"O Gemini falhou após {self.MAX_RETRIES} tentativas devido a: {msg}")
                        
                    await asyncio.sleep(espera)
                else:
                    raise e

    async def transcrever_audio(self, caminho_local: str) -> str:
        """
        Faz o upload do arquivo de áudio local para a File API do Gemini,
        aguarda que o processamento esteja ACTIVE e transcreve o conteúdo.
        """
        loop = asyncio.get_running_loop()

        # Passo 1: Upload
        logger.info(f"Enviando o arquivo '{caminho_local}' para a File API do Gemini...")
        
        def _upload():
            return self.client.files.upload(file=caminho_local)
            
        ficheiro_gemini = await loop.run_in_executor(None, _upload)
        logger.info(f"Arquivo enviado. URI: {ficheiro_gemini.uri}")

        # Passo 2: Aguardar ACTIVE
        def _aguardar_active():
            f = self.client.files.get(name=ficheiro_gemini.name)
            while f.state.name == "PROCESSING":
                logger.info(f"Aguardando processamento do arquivo... (estado: {f.state.name})")
                time.sleep(self.INTERVALO_ESPERA_SEGUNDOS)
                f = self.client.files.get(name=ficheiro_gemini.name)
            if f.state.name == "FAILED":
                raise RuntimeError("O processamento do arquivo de áudio no Gemini falhou.")
            logger.info("Arquivo no estado ACTIVE. Pronto para transcrição.")
            return f

        ficheiro_ativo = await loop.run_in_executor(None, _aguardar_active)

        # Passo 3: Transcrever com retry
        logger.info(f"Transcrevendo o áudio com o modelo {self.MODELO_TRANSCRICAO}...")
        
        def _call_generate():
            return self.client.models.generate_content(
                model=self.MODELO_TRANSCRICAO,
                contents=[ficheiro_ativo, "Por favor, transcreve este áudio."]
            )
            
        resposta = await self._executar_com_retry(_call_generate)
        transcricao = resposta.text

        # Passo 4: Apagar
        def _delete():
            self.client.files.delete(name=ficheiro_gemini.name)
            
        await loop.run_in_executor(None, _delete)
        logger.info(f"Arquivo '{ficheiro_gemini.name}' apagado da File API.")

        return transcricao

    async def gerar_cronica_epica(self, transcricao: str) -> str:
        """
        Gera uma crônica épica de RPG em Markdown usando o modelo Gemini.
        """
        logger.info(f"Gerando a Crônica Épica com o modelo {self.MODELO_CRONICA}...")

        prompt = (
            "És um Mestre de RPG veterano. Pega no seguinte resumo bruto de uma sessão e "
            "transforma-o numa crônica épica, formatada em Markdown, focando-te nas ações dos jogadores, "
            "itens encontrados e ganchos da história. Resumo bruto:\n\n" + transcricao
        )

        def _call_generate():
            return self.client.models.generate_content(
                model=self.MODELO_CRONICA,
                contents=prompt
            )

        resposta = await self._executar_com_retry(_call_generate)
        return resposta.text

