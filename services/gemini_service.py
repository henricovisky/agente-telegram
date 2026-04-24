import time
import asyncio
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
        import re
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

    async def chat(self, mensagem: str, user_id: int, historico: list[dict] | None = None) -> str:
        """Chat com histórico, compressão automática e RAG pessoal."""
        historico = historico or []
        
        # 1. Compressão automática de histórico
        if len(historico) >= 16:
            logger.info(f"📦 Comprimindo histórico para {user_id}...")
            velho_hist = historico[:-4]
            texto_velho = "\n".join([f"{m['role']}: {m['content']}" for m in velho_hist])
            
            prompt_comp = get_prompt("compress.historico")["template"].format(historico=texto_velho)
            try:
                def _call_comp(): return self.client.models.generate_content(model='gemini-2.0-flash-lite', contents=prompt_comp)
                res_comp = await self._executar_com_retry(_call_comp)
                resumo = res_comp.text.strip()
                historico = [{"role": "system", "content": f"Resumo da conversa anterior: {resumo}"}] + historico[-4:]
            except Exception as e:
                logger.error(f"Falha na compressão: {e}")

        # 2. Busca contexto de memória de longo prazo (RAG)
        memoria_contexto = await self.ltm.get_relevant_context(user_id, mensagem)

        # 3. Ferramentas (Tools)
        def exec_terminal(command: str) -> str: return terminal_service.execute(command)
        async def lembrar_fato(fato: str) -> str:
            ok = await self.ltm.save_fact(user_id, fato)
            return "Fato memorizado com sucesso." if ok else "Erro ao memorizar fato."

        tools = [exec_terminal, lembrar_fato]

        # 4. Formata conteúdos
        contents = []
        for turno in historico:
            role = "user" if turno["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": turno["content"]}]})
        
        contents.append({"role": "user", "parts": [{"text": mensagem}]})

        # 5. Tentativa de resposta com Fallback
        modelos_tentativa = [self.MODELO_CHAT] + self.MODELOS_BACKUP
        ultima_excecao = None
        for modelo_atual in modelos_tentativa:
            try:
                persona_key = conversation_service.get_persona(user_id)
                persona = get_persona(persona_key)
                
                sys_inst = persona["prompt"]
                if memoria_contexto:
                    sys_inst += f"\n\n{memoria_contexto}"

                if "gemma" in modelo_atual:
                    config = types.GenerateContentConfig(automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
                else:
                    config = types.GenerateContentConfig(
                        system_instruction=sys_inst,
                        tools=tools,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False)
                    )

                def _call(): return self.client.models.generate_content(model=modelo_atual, contents=contents, config=config)
                resposta = await self._executar_com_retry(_call)
                if not resposta or not resposta.text: continue

                texto = resposta.text.strip()
                input_chars = sum(len(p.get("text", "")) for c in contents for p in c.get("parts", []))
                token_manager.registrar_uso(modelo_atual, input_chars, len(texto))
                return texto

            except Exception as e:
                ultima_excecao = e
                if any(err in str(e).lower() for err in ["429", "quota", "503", "limit"]):
                    logger.warning(f"⚠️ {modelo_atual} sem cota. Próximo...")
                    continue
                logger.error(f"Erro em {modelo_atual}: {e}")
                break

        return f"❌ Todos os modelos falharam. Último erro: {str(ultima_excecao)}"
