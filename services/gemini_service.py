import time
import asyncio
import re
import math
import textwrap
from google import genai
from google.genai import types
from google.genai.errors import APIError

from config import GEMINI_API_KEY, logger
from agent.prompt_registry import get as get_prompt
from agent.token_manager import token_manager
from agent.persona_registry import get_persona
from services.terminal_service import terminal_service
from services.conversation_service import conversation_service
from agent.long_term_memory import LongTermMemory


class GeminiService:
    """
    Encapsula todas as operações com a API do Google Gemini.
    Responsável por: upload de arquivos pesados via File API,
    transcrição de áudio e geração da crônica épica de RPG.
    """
    # Modelos Principais
    MODELO_TRANSCRICAO = 'gemini-2.5-flash-lite'
    MODELO_CRONICA     = 'gemini-2.5-flash-lite'
    MODELO_CHAT        = 'gemini-3-flash-lite-preview'

    # Modelos de Backup
    MODELOS_BACKUP = [
        'gemini-3.1-flash-preview',
        'gemma-4-26b-a4b-it',
        'gemma-3-27b-it',
        'gemma-3-4b-it'
    ]

    # Intervalo de espera base (em segundos)
    INTERVALO_ESPERA_SEGUNDOS = 30
    MAX_RETRIES = 5
    
    @classmethod
    def get_available_models(cls) -> list[str]:
        """Retorna a lista de todos os modelos disponíveis (principal + backups)."""
        return [cls.MODELO_CHAT] + cls.MODELOS_BACKUP

    def __init__(self, api_key: str = GEMINI_API_KEY):
        """
        Inicializa o serviço e configura o cliente da nova API do Gemini.
        """
        if not api_key:
            raise ValueError("A GEMINI_API_KEY não foi fornecida. Verifique o arquivo .env.")
        self.client = genai.Client(api_key=api_key)
        self.ltm = LongTermMemory(self)

    async def _executar_com_retry(self, func, *args, **kwargs):
        """
        Executa uma função síncrona com retry em caso de Rate Limit (429) ou 503.
        """
        loop = asyncio.get_running_loop()
        tentativa = 0
        while tentativa < self.MAX_RETRIES:
            try:
                return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
            except Exception as e:
                msg = str(e)
                if any(err in msg for err in ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"]):
                    if "limit: 0" in msg or "PerDay" in msg:
                        logger.error("Cota diária do Gemini esgotada.")
                        raise RuntimeError(f"QUOTA_EXHAUSTED: {msg}")
                    tentativa += 1
                    espera = float(self.INTERVALO_ESPERA_SEGUNDOS * (2 ** (tentativa - 1)))
                    match = re.search(r"retry in ([\d\.]+)s", msg)
                    if match:
                        try:
                            espera = float(match.group(1)) + 2.0
                        except ValueError:
                            pass
                    logger.warning(f"Tentativa {tentativa}/{self.MAX_RETRIES}. Aguardando {espera:.1f}s...")
                    if tentativa >= self.MAX_RETRIES:
                        raise RuntimeError(f"O Gemini falhou após {self.MAX_RETRIES} tentativas: {msg}")
                    await asyncio.sleep(espera)
                else:
                    raise e

    async def transcrever_audio(self, caminho_local: str) -> str:
        """Upload e transcrição de áudio."""
        loop = asyncio.get_running_loop()
        logger.info(f"Enviando '{caminho_local}' para File API...")
        def _upload(): return self.client.files.upload(file=caminho_local)
        ficheiro_gemini = await loop.run_in_executor(None, _upload)

        def _aguardar_active():
            f = self.client.files.get(name=ficheiro_gemini.name)
            while f.state.name == "PROCESSING":
                time.sleep(self.INTERVALO_ESPERA_SEGUNDOS)
                f = self.client.files.get(name=ficheiro_gemini.name)
            return f
        ficheiro_ativo = await loop.run_in_executor(None, _aguardar_active)

        modelos = [self.MODELO_TRANSCRICAO] + self.MODELOS_BACKUP
        transcricao = None
        for mod in modelos:
            if "gemma" in mod: continue
            try:
                def _call(): return self.client.models.generate_content(model=mod, contents=[ficheiro_ativo, "Transcreva este áudio."])
                resposta = await self._executar_com_retry(_call)
                transcricao = resposta.text
                break
            except Exception: continue

        await loop.run_in_executor(None, lambda: self.client.files.delete(name=ficheiro_gemini.name))
        return transcricao or "Falha na transcrição."

    async def gerar_cronica_epica(self, transcricao: str) -> str:
        """Gera crônica de RPG usando RAG interno se necessário."""
        logger.info(f"Gerando a Crônica Épica...")
        
        LIMITE_CARACTERES = 15000
        if len(transcricao) > LIMITE_CARACTERES:
            logger.info(f"Transcrição longa ({len(transcricao)} caracteres). Iniciando processo RAG...")
            
            def _get_cosine_similarity(v1, v2):
                dot = sum(a * b for a, b in zip(v1, v2))
                norm1 = math.sqrt(sum(a * a for a in v1))
                norm2 = math.sqrt(sum(b * b for b in v2))
                if norm1 == 0 or norm2 == 0: return 0.0
                return dot / (norm1 * norm2)
            
            chunks = textwrap.wrap(transcricao, width=1500, break_long_words=False, replace_whitespace=False)
            
            def _embed(texts):
                return self.client.models.embed_content(
                    model='text-embedding-004',
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
        for mod in modelos:
            try:
                def _call(): return self.client.models.generate_content(model=mod, contents=prompt)
                res = await self._executar_com_retry(_call)
                token_manager.registrar_uso(mod, len(prompt), len(res.text))
                return res.text
            except Exception: continue
        return "Erro ao gerar crônica."

    async def chat(self, mensagem: str, user_id: int, historico: list[dict] | None = None, on_thought: callable = None) -> str:
        """Chat com histórico, compressão automática e RAG pessoal."""
        historico = historico or []
        resumo_historico = None
        
        # 1. Compressão automática de histórico
        if len(historico) >= 16:
            logger.info(f"📦 Comprimindo histórico para {user_id}...")
            velho_hist = historico[:-4]
            texto_velho = "\n".join([f"{m['role']}: {m['content']}" for m in velho_hist])
            
            prompt_comp = get_prompt("compress.historico")["template"].format(historico=texto_velho)
            try:
                def _call_comp(): return self.client.models.generate_content(model='gemini-2.0-flash-lite', contents=prompt_comp)
                res_comp = await self._executar_com_retry(_call_comp)
                resumo_historico = res_comp.text.strip()
                # Mantém apenas os últimos 4 turnos reais
                historico = historico[-4:]
            except Exception as e:
                logger.error(f"Falha na compressão: {e}")

        # 2. Busca contexto de memória de longo prazo (RAG)
        memoria_contexto = await self.ltm.get_relevant_context(user_id, mensagem)

        # 3. Ferramentas (Tools)
        # Definimos as funções que podem ser chamadas
        async def exec_terminal_tool(command: str) -> str:
            return terminal_service.execute(command)

        async def lembrar_fato_tool(fato: str) -> str:
            ok = await self.ltm.save_fact(user_id, fato)
            return "Fato memorizado com sucesso." if ok else "Erro ao memorizar fato."

        # Mapeamento para execução manual
        tool_map = {
            "exec_terminal": exec_terminal_tool,
            "lembrar_fato": lembrar_fato_tool
        }
        
        # Definições com docstrings para o Gemini (Schema extraction)
        def exec_terminal(command: str) -> str:
            """Executa um comando bash no servidor e retorna a saída."""
            ...
        def lembrar_fato(fato: str) -> str:
            """Memoriza um fato importante sobre o usuário para consultas futuras."""
            ...
        
        tools = [exec_terminal, lembrar_fato]

        # 4. Formata conteúdos (Histórico)
        # Gemini exige que a conversa comece com 'user' e alterne roles.
        contents_base = []
        for turno in historico:
            role = "user" if turno["role"] == "user" else "model"
            contents_base.append(types.Content(role=role, parts=[types.Part(text=turno["content"])]))
        
        # Garante que começa com user se o histórico estiver "desalinhado" (segurança)
        if contents_base and contents_base[0].role == "model":
            contents_base = contents_base[1:]

        # 5. Tentativa de resposta com Fallback e Loop ReAct
        preferencia = conversation_service.get_model(user_id)
        if preferencia:
            modelos_tentativa = [preferencia] + [m for m in [self.MODELO_CHAT] + self.MODELOS_BACKUP if m != preferencia]
        else:
            modelos_tentativa = [self.MODELO_CHAT] + self.MODELOS_BACKUP
            
        ultima_excecao = None
        
        for modelo_atual in modelos_tentativa:
            try:
                persona_key = conversation_service.get_persona(user_id)
                persona = get_persona(persona_key)
                
                sys_inst = persona["prompt"]
                if resumo_historico:
                    sys_inst += f"\n\nResumo da conversa anterior:\n{resumo_historico}"
                if memoria_contexto:
                    sys_inst += f"\n\nContexto da sua memória sobre este usuário:\n{memoria_contexto}"

                # Reset do context para esta tentativa
                contents = list(contents_base)
                contents.append(types.Content(role="user", parts=[types.Part(text=mensagem)]))

                # Se for Gemma, desabilita ferramentas por enquanto (suporte limitado)
                tools_to_use = None if "gemma" in modelo_atual else tools

                # Loop ReAct manual
                max_steps = 5
                current_step = 0
                texto_final_acumulado = []

                while current_step < max_steps:
                    current_step += 1
                    
                    config = types.GenerateContentConfig(
                        system_instruction=sys_inst,
                        tools=tools_to_use,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                    )

                    def _call(): return self.client.models.generate_content(model=modelo_atual, contents=contents, config=config)
                    resposta = await self._executar_com_retry(_call)
                    
                    if not resposta or not resposta.candidates:
                        break

                    candidate = resposta.candidates[0]
                    parts = candidate.content.parts
                    
                    # Adiciona a resposta do modelo ao contexto da chamada
                    contents.append(candidate.content)
                    
                    # 1. Processa Texto e Thoughts
                    texto_deste_passo = ""
                    for part in parts:
                        if part.text:
                            texto_parte = part.text
                            # Extrai <thought> se existir
                            match = re.search(r"<thought>(.*?)</thought>", texto_parte, re.DOTALL)
                            if match:
                                if on_thought:
                                    await on_thought(match.group(1).strip())
                                # Remove o thought do texto que será enviado ao usuário
                                texto_parte = re.sub(r"<thought>.*?</thought>", "", texto_parte, flags=re.DOTALL).strip()
                            
                            if texto_parte:
                                texto_deste_passo += texto_parte
                    
                    if texto_deste_passo:
                        texto_final_acumulado.append(texto_deste_passo)

                    # 2. Processa Function Calls
                    function_calls = [p.function_call for p in parts if p.function_call]
                    
                    if not function_calls:
                        # Resposta final
                        final_str = "\n\n".join(texto_final_acumulado).strip()
                        token_manager.registrar_uso(modelo_atual, 0, len(final_str))
                        return final_str

                    # Executa ferramentas
                    tool_parts = []
                    for fc in function_calls:
                        name = fc.name
                        args = fc.args
                        logger.info(f"🛠️ Executando ferramenta: {name}({args})")
                        
                        if name in tool_map:
                            try:
                                result = await tool_map[name](**args)
                            except Exception as e:
                                result = f"Erro ao executar {name}: {str(e)}"
                        else:
                            result = f"Ferramenta {name} não encontrada."
                        
                        tool_parts.append(types.Part(
                            function_response=types.FunctionResponse(
                                name=name,
                                response={"result": result}
                            )
                        ))
                    
                    # Adiciona resultados das ferramentas ao contexto
                    contents.append(types.Content(role="user", parts=tool_parts))
                
                return "A tarefa atingiu o limite de passos ReAct."

            except Exception as e:
                ultima_excecao = e
                logger.warning(f"⚠️ Erro no modelo {modelo_atual}: {e}")
                # Continua para o próximo modelo se houver falha
                continue

        return f"❌ Todos os modelos falharam. Último erro: {str(ultima_excecao)}"
