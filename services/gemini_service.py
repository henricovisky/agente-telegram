import time
import asyncio
from google import genai
from google.genai import types
from google.genai.errors import APIError

from config import GEMINI_API_KEY, logger
from agent.prompt_registry import get as get_prompt
from agent.token_manager import token_manager
from services.terminal_service import terminal_service


class GeminiService:
    """
    Encapsula todas as operações com a API do Google Gemini.
    Responsável por: upload de arquivos pesados via File API,
    transcrição de áudio e geração da crônica épica de RPG.
    """
    # Modelos Principais
    MODELO_TRANSCRICAO = 'gemini-2.5-flash-lite'
    MODELO_CRONICA     = 'gemini-2.5-flash-lite'
    MODELO_CHAT        = 'gemini-3-flash-preview'

    # Modelos de Backup (solicitados pelo usuário)
    MODELOS_BACKUP = [
        'gemini-3.1-flash-lite-preview',
        'gemma-4-26b-a4b-it',
        'gemma-3-27b-it',
        'gemma-3-4b-it'
    ]

    # System prompt do agente pessoal
    SYSTEM_PROMPT = (
        "Você é Henricovisky, um agente pessoal de IA que roda localmente no servidor Jarvis do Henrique. "
        "Responda sempre em português do Brasil de forma direta, precisa e sem ser prolixo. "
        "Você é um especialista em Linux e Python. "
        "Você tem 'Poderes de Terminal': você pode executar comandos bash diretamente no servidor para verificar arquivos, "
        "verificar processos, logs, ou realizar tarefas administrativas que o usuário solicitar. "
        "Sempre verifique o resultado do comando antes de confirmar ao usuário. "
        "Use o terminal com sabedoria e responsabilidade. "
        "Além disso, você tem acesso ao Google Drive e geração de PDF. "
        "Não se estenda muito nas respostas, diga tudo que precisa ser dito em no máximo 5 frases."
    )

    # Intervalo de espera base (em segundos)
    INTERVALO_ESPERA_SEGUNDOS = 30
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
        Executa uma função síncrona com retry em caso de Rate Limit (429) ou 503.
        Distingue entre rate limit por minuto (recuperável via retry) e
        quota diária esgotada (falha imediata, retry não adianta).
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
                    
                    # --- Detecção de quota diária esgotada (NÃO recuperável com retry) ---
                    if "limit: 0" in msg or "PerDay" in msg:
                        logger.error("Cota diária do Gemini esgotada.")
                        # Lançamos uma exceção específica para o fallback capturar
                        raise RuntimeError(f"QUOTA_EXHAUSTED: {msg}")

                    tentativa += 1
                    
                    # Backoff exponencial base
                    espera = float(self.INTERVALO_ESPERA_SEGUNDOS * (2 ** (tentativa - 1)))
                    
                    # Tentar extrair o tempo de espera exato da mensagem
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

        # Passo 3: Transcrever com retry e fallback de modelo
        modelos = [self.MODELO_TRANSCRICAO] + self.MODELOS_BACKUP
        transcricao = None
        ultima_excecao = None

        for modelo_atual in modelos:
            if "gemma" in modelo_atual:
                continue

            logger.info(f"Tentando transcrição com o modelo {modelo_atual}...")
            try:
                def _call_generate():
                    return self.client.models.generate_content(
                        model=modelo_atual,
                        contents=[ficheiro_ativo, "Por favor, transcreve este áudio."]
                    )
                resposta = await self._executar_com_retry(_call_generate)
                transcricao = resposta.text
                break
            except Exception as e:
                ultima_excecao = e
                if "QUOTA_EXHAUSTED" in str(e):
                    logger.warning(f"Cota esgotada para {modelo_atual}. Tentando próximo...")
                    continue
                raise e

        if not transcricao:
            raise ultima_excecao or RuntimeError("Falha total na transcrição.")

        # Passo 4: Apagar
        def _delete():
            self.client.files.delete(name=ficheiro_gemini.name)
            
        await loop.run_in_executor(None, _delete)
        logger.info(f"Arquivo '{ficheiro_gemini.name}' apagado da File API.")

        return transcricao

    async def gerar_cronica_epica(self, transcricao: str) -> str:
        """
        Gera uma crônica épica de RPG em Markdown usando o modelo Gemini.
        Utiliza RAG (Retrieval-Augmented Generation) para reduzir textos longos.
        """
        logger.info(f"Gerando a Crônica Épica...")
        
        # --- Lógica de RAG para reduzir tamanho da transcrição ---
        LIMITE_CARACTERES = 15000
        if len(transcricao) > LIMITE_CARACTERES:
            logger.info(f"Transcrição longa ({len(transcricao)} caracteres). Iniciando processo RAG...")
            
            import textwrap
            import math
            
            def _get_cosine_similarity(v1, v2):
                dot = sum(a * b for a, b in zip(v1, v2))
                norm1 = math.sqrt(sum(a * a for a in v1))
                norm2 = math.sqrt(sum(b * b for b in v2))
                if norm1 == 0 or norm2 == 0: return 0.0
                return dot / (norm1 * norm2)
            
            chunks = textwrap.wrap(transcricao, width=1500, break_long_words=False, replace_whitespace=False)
            
            def _embed(texts):
                return self.client.models.embed_content(
                    model='gemini-embedding-001',
                    contents=texts
                )
            
            embeddings_chunks = []
            lote_tamanho = 100
            for i in range(0, len(chunks), lote_tamanho):
                lote = chunks[i:i+lote_tamanho]
                res = await self._executar_com_retry(_embed, lote)
                for e in res.embeddings:
                    embeddings_chunks.append(e.values)
                    
            queries = [
                "início da sessão e recapitulação",
                "combates épicos, lutas, magias",
                "roleplay, conversas marcantes, piadas",
                "regras de Dungeons and Dragons 5e"
            ]
            
            res_queries = await self._executar_com_retry(_embed, queries)
            embeddings_queries = [e.values for e in res_queries.embeddings]
            
            K = 6 
            indices_selecionados = set()
            for q_emb in embeddings_queries:
                similaridades = sorted([(idx, _get_cosine_similarity(q_emb, c_emb)) for idx, c_emb in enumerate(embeddings_chunks)], key=lambda x: x[1], reverse=True)
                for idx, sim in similaridades[:K]:
                    indices_selecionados.add(idx)
                    
            indices_ordenados = sorted(list(indices_selecionados))
            transcricao = "\n\n[...] (trecho pulado pelo RAG) [...]\n\n".join([chunks[i] for i in indices_ordenados])
            logger.info(f"RAG concluído. Tamanho reduzido para {len(transcricao)} caracteres.")

        prompt_cfg = get_prompt("rpg.cronica")
        prompt = prompt_cfg["template"].format(transcricao=transcricao)

        modelos = [self.MODELO_CRONICA] + self.MODELOS_BACKUP
        cronica = None
        ultima_excecao = None

        for modelo_atual in modelos:
            try:
                logger.info(f"Tentando gerar crônica com {modelo_atual}...")
                def _call_generate():
                    return self.client.models.generate_content(
                        model=modelo_atual,
                        contents=prompt
                    )
                resposta = await self._executar_com_retry(_call_generate)
                cronica = resposta.text
                token_manager.registrar_uso(modelo_atual, len(prompt), len(cronica))
                break
            except Exception as e:
                ultima_excecao = e
                if "QUOTA_EXHAUSTED" in str(e):
                    continue
                raise e

        return cronica or "Erro ao gerar crônica."

    async def chat(self, mensagem: str, historico: list[dict] | None = None) -> str:
        """
        Envia uma mensagem livre ao Gemini com suporte a ferramentas e fallback multi-modelo.
        """
        historico = historico or []

        def exec_terminal(command: str) -> str:
            return terminal_service.execute(command)

        tools = [exec_terminal]

        contents = []
        for turno in historico:
            role = "user" if turno["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": turno["content"]}]
            })
        
        contents.append({
            "role": "user",
            "parts": [{"text": mensagem}]
        })

        modelos_tentativa = [self.MODELO_CHAT] + self.MODELOS_BACKUP
        ultima_excecao = None

        for modelo_atual in modelos_tentativa:
            try:
                logger.info(f"💬 Chat com modelo: {modelo_atual}")
                
                if "gemma" in modelo_atual:
                    config = types.GenerateContentConfig(
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                    )
                else:
                    config = types.GenerateContentConfig(
                        system_instruction=self.SYSTEM_PROMPT,
                        tools=tools,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False)
                    )

                def _call():
                    return self.client.models.generate_content(
                        model=modelo_atual,
                        contents=contents,
                        config=config
                    )

                resposta = await self._executar_com_retry(_call)
                if not resposta or not resposta.text:
                    continue

                texto = resposta.text.strip()
                input_chars = sum(len(p.get("text", "")) for c in contents for p in c.get("parts", []))
                token_manager.registrar_uso(modelo_atual, input_chars, len(texto))

                return texto

            except Exception as e:
                ultima_excecao = e
                msg_erro = str(e).lower()
                if any(err in msg_erro for err in ["429", "quota_exhausted", "503", "limit"]):
                    logger.warning(f"⚠️ Modelo {modelo_atual} sem cota. Tentando próximo...")
                    continue
                else:
                    logger.error(f"Erro no modelo {modelo_atual}: {str(e)}")
                    break

        return f"❌ Todos os modelos falharam. Último erro: {str(ultima_excecao)}"
