import math
from services.memory_service import memory_service
from config import logger

class LongTermMemory:
    """
    Gerencia a memória de longo prazo (RAG) do usuário.
    Permite salvar fatos e recuperar os mais relevantes via similaridade de cosseno.
    """

    def __init__(self, gemini_service):
        self.gemini = gemini_service

    async def save_fact(self, user_id: int, fact: str):
        """Transforma um fato em embedding e salva no banco."""
        try:
            uid = str(user_id)
            logger.info(f"🧠 Salvando fato para {uid}: {fact}")
            
            # Gera embedding usando o Gemini
            res = await self.gemini.client.models.embed_content(
                model='text-embedding-004',
                contents=[fact]
            )
            embedding = res.embeddings[0].values
            
            memory_service.salvar_fato(uid, fact, embedding)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar fato: {str(e)}")
            return False

    async def get_relevant_context(self, user_id: int, query: str, top_k: int = 3) -> str:
        """Busca os fatos mais relevantes para uma query."""
        try:
            uid = str(user_id)
            fatos = memory_service.buscar_fatos(uid)
            if not fatos:
                return ""

            # Gera embedding da query
            res = await self.gemini.client.models.embed_content(
                model='text-embedding-004',
                contents=[query]
            )
            q_emb = res.embeddings[0].values

            def cosine_similarity(v1, v2):
                dot = sum(a * b for a, b in zip(v1, v2))
                norm1 = math.sqrt(sum(a * a for a in v1))
                norm2 = math.sqrt(sum(b * b for b in v2))
                if norm1 == 0 or norm2 == 0: return 0.0
                return dot / (norm1 * norm2)

            # Calcula similaridade e ordena
            scored = []
            for f in fatos:
                sim = cosine_similarity(q_emb, f["embedding"])
                if sim > 0.65: # Threshold de relevância
                    scored.append((sim, f["fact"]))
            
            scored.sort(key=lambda x: x[0], reverse=True)
            top_facts = [f[1] for f in scored[:top_k]]
            
            if not top_facts:
                return ""
                
            context = "\n".join([f"- {f}" for f in top_facts])
            return f"\n[CONTEXTO DE MEMÓRIA DE LONGO PRAZO]\n{context}\n"
            
        except Exception as e:
            logger.error(f"Erro ao buscar memória: {str(e)}")
            return ""
