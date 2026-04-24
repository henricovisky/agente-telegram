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
    # Modelos
    MODELO_TRANSCRICAO = 'gemini-2.5-flash-lite'
    MODELO_CRONICA     = 'gemini-2.5-flash-lite'
    MODELO_CHAT        = 'gemini-3-flash-preview'

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
                    # Quando "limit: 0" aparece, a cota do dia ou do projeto acabou.
                    # Tentar de novo nunca vai funcionar — falha imediata.
                    if "limit: 0" in msg or "PerDay" in msg:
                        logger.error("Cota diária do Gemini esgotada. Não é possível recuperar via retry.")
                        raise RuntimeError(
                            "⚠️ A cota diária da API do Gemini foi esgotada. "
                            "Aguarde a renovação (geralmente meia-noite, horário do Pacífico) "
                            "ou ative o faturamento no Google AI Studio."
                        )

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
        Utiliza RAG (Retrieval-Augmented Generation) para reduzir textos longos
        e poupar tokens.
        """
        logger.info(f"Gerando a Crônica Épica com o modelo {self.MODELO_CRONICA}...")
        
        loop = asyncio.get_running_loop()
        
        # --- Lógica de RAG para reduzir tamanho da transcrição ---
        LIMITE_CARACTERES = 15000
        if len(transcricao) > LIMITE_CARACTERES:
            logger.info(f"Transcrição longa ({len(transcricao)} caracteres). Iniciando processo RAG para redução...")
            
            import textwrap
            import math
            
            def _get_cosine_similarity(v1, v2):
                dot = sum(a * b for a, b in zip(v1, v2))
                norm1 = math.sqrt(sum(a * a for a in v1))
                norm2 = math.sqrt(sum(b * b for b in v2))
                if norm1 == 0 or norm2 == 0: return 0.0
                return dot / (norm1 * norm2)
            
            # 1. Divisão em chunks
            chunks = textwrap.wrap(transcricao, width=1500, break_long_words=False, replace_whitespace=False)
            logger.info(f"Texto dividido em {len(chunks)} chunks. Gerando embeddings...")
            
            def _embed(texts):
                return self.client.models.embed_content(
                    model='gemini-embedding-001',
                    contents=texts
                )
            
            # Embeddings dos chunks (em lotes para evitar erro de limite)
            embeddings_chunks = []
            lote_tamanho = 100
            for i in range(0, len(chunks), lote_tamanho):
                lote = chunks[i:i+lote_tamanho]
                res = await self._executar_com_retry(_embed, lote)
                for e in res.embeddings:
                    embeddings_chunks.append(e.values)
                    
            # 2. Definição das queries do RAG para as seções necessárias
            queries = [
                "início da sessão e recapitulação do que aconteceu antes",
                "combates épicos, lutas, batalhas, magias lançadas, ataques, dano, mortes, rolagens de dados",
                "roleplay, conversas marcantes, piadas, interações engraçadas, decisões de história e NPCs",
                "regras de Dungeons and Dragons 5e, táticas, dicas de sobrevivência, uso de habilidades"
            ]
            
            res_queries = await self._executar_com_retry(_embed, queries)
            embeddings_queries = [e.values for e in res_queries.embeddings]
            
            # 3. Busca dos Top-K chunks por query
            K = 6 # Total máximo de chunks: 4 queries * 6 = 24 chunks (~36.000 chars)
            indices_selecionados = set()
            
            for q_emb in embeddings_queries:
                similaridades = []
                for idx, c_emb in enumerate(embeddings_chunks):
                    sim = _get_cosine_similarity(q_emb, c_emb)
                    similaridades.append((idx, sim))
                similaridades.sort(key=lambda x: x[1], reverse=True)
                for idx, sim in similaridades[:K]:
                    indices_selecionados.add(idx)
                    
            # 4. Reconstrução do texto ordenado cronologicamente
            indices_ordenados = sorted(list(indices_selecionados))
            transcricao_reduzida = "\n\n[...] (trecho pulado pelo RAG) [...]\n\n".join([chunks[i] for i in indices_ordenados])
            
            logger.info(f"RAG concluído. Tamanho reduzido de {len(transcricao)} para {len(transcricao_reduzida)} caracteres.")
            transcricao = transcricao_reduzida

        prompt_cfg = get_prompt("rpg.cronica")
        prompt = prompt_cfg["template"].format(transcricao=transcricao)

        def _call_generate():
            return self.client.models.generate_content(
                model=self.MODELO_CRONICA,
                contents=prompt
            )

        resposta = await self._executar_com_retry(_call_generate)
        cronica = resposta.text

        # Registra uso estimado de tokens
        token_manager.registrar_uso(self.MODELO_CRONICA, len(prompt), len(cronica))

        return cronica

    async def chat(self, mensagem: str, historico: list[dict] | None = None) -> str:
        """
        Envia uma mensagem livre ao Gemini com histórico multi-turno e suporte a ferramentas.
        """
        historico = historico or []

        # Configura as ferramentas (tools)
        def exec_terminal(command: str) -> str:
            """
            Executa um comando no terminal Linux do servidor.
            """
            return terminal_service.execute(command)

        tools = [exec_terminal]

        # Constrói o histórico no formato esperado pelo SDK (ChatSession)
        contents = []
        for turno in historico:
            role = "user" if turno["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": turno["content"]}]
            })
        
        # Adiciona a mensagem atual
        contents.append({
            "role": "user",
            "parts": [{"text": mensagem}]
        })

        # Configuração da sessão de chat com function calling automático
        config = types.GenerateContentConfig(
            system_instruction=self.SYSTEM_PROMPT,
            tools=tools,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False)
        )

        try:
            # Usando generate_content diretamente com o histórico completo para simplificar
            # e garantir que o system_instruction seja respeitado em cada chamada.
            def _call():
                return self.client.models.generate_content(
                    model=self.MODELO_CHAT,
                    contents=contents,
                    config=config
                )

            resposta = await self._executar_com_retry(_call)
            
            if not resposta or not resposta.text:
                # Caso o modelo tenha apenas retornado chamadas de função (o que o automatic_function_calling deve resolver)
                # ou tenha dado algum erro silencioso.
                return "Desculpe, não consegui processar sua mensagem."

            texto = resposta.text.strip()
            
            # Registro de uso aproximado
            input_chars = 0
            for c in contents:
                for p in c.get("parts", []):
                    input_chars += len(p.get("text", ""))
            token_manager.registrar_uso(self.MODELO_CHAT, input_chars, len(texto))

            return texto

        except Exception as e:
            logger.error(f"Erro no chat Gemini: {str(e)}")
            return f"❌ Erro ao processar mensagem: {str(e)}"

