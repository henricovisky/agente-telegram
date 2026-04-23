# 🧠 Oráculo de Mesa — Arquitetura de Agente Pessoal

**Versão:** 3.0  
**Data:** 2026-04-23  
**Status:** Planejamento (aguardando aprovação para implementação)

---

## 1. Visão: O que é este bot?

O **Oráculo de Mesa** é um **agente de IA pessoal** que vive no Telegram. A ideia central é:

> Você fala com ele por comando (`/comando`), ele pensa com o Gemini, age no mundo real (Drive, arquivos, APIs), e responde com resultado útil — como um assistente inteligente, mas sem custos de assinatura e sem limites de uso impostos por plataforma.

Pense nele como seu próprio **Claude Projects** ou **OpenAI Assistants**, só que:
- Rodando no **seu servidor** (você controla tudo)
- Usando o **Gemini gratuito** (com gestão agressiva de tokens)
- Comandos **ilimitados e customizáveis** (você adiciona o que quiser)
- **Sem interface web** — o Telegram é a sua UI

---

## 2. Os Três Pilares do Agente

```
┌─────────────────────────────────────────────────────────┐
│                     USUÁRIO (Telegram)                  │
└─────────────────────┬───────────────────────────────────┘
                      │ /comando [args]
                      ▼
┌─────────────────────────────────────────────────────────┐
│              PILAR 1: NÚCLEO DO AGENTE                  │
│   • Recebe o comando                                    │
│   • Gerencia contexto e memória da conversa             │
│   • Controla orçamento de tokens                        │
│   • Chama o módulo correto                              │
└──────────────┬──────────────────────────┬───────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────┐  ┌───────────────────────────┐
│  PILAR 2: MÓDULOS        │  │  PILAR 3: SERVIÇOS        │
│  (O que o bot FAZ)       │  │  (Como o bot ACESSA o     │
│                          │  │   mundo externo)           │
│  • bot/modules/rpg.py    │  │                           │
│  • bot/modules/core.py   │  │  • services/gemini.py     │
│  • bot/modules/[novo].py │  │  • services/drive.py      │
│                          │  │  • services/pdf.py        │
│  Cada módulo = um tema   │  │  • services/memory.py     │
│  de automações           │  │  • services/tokens.py     │
└──────────────────────────┘  └───────────────────────────┘
```

---

## 3. Estrutura de Pastas — Visão Completa

```
agente-reuniao/
│
├── main.py                     # Boot: monta o bot e registra módulos
├── config.py                   # Variáveis de ambiente, logging, constantes globais
├── requirements.txt
├── .env                        # Segredos (NÃO versionar)
├── .env.example
├── .gitignore
│
├── agent/                      # Núcleo do agente (lógica inteligente)
│   ├── __init__.py
│   ├── context.py              # Gerencia o contexto e histórico de conversa por chat_id
│   ├── token_manager.py        # Contabilidade e economia de tokens
│   └── prompt_registry.py     # Repositório central de prompts versionados
│
├── bot/                        # Camada Telegram
│   ├── __init__.py
│   ├── registry.py             # Mapeia /comandos → handlers de módulos
│   ├── middleware.py           # Pré/pós-processamento (logging, auth, rate limit)
│   └── modules/                # ← Um arquivo por tema de automação
│       ├── __init__.py
│       ├── core.py             # /start, /ajuda, /status, /memoria
│       ├── rpg.py              # /rpg_transcrever, /rpg_resumo
│       └── [novo_modulo].py    # Qualquer novo tema
│
├── services/                   # Integrações externas (stateless, reutilizáveis)
│   ├── __init__.py
│   ├── gemini_service.py       # LLM: geração, transcrição, embeddings + retry
│   ├── drive_service.py        # Google Drive: upload, download, busca
│   ├── pdf_service.py          # Markdown → PDF (fpdf2)
│   └── memory_service.py       # Persistência de memória em SQLite
│
├── data/                       # Dados locais persistidos (NÃO versionar)
│   └── memory.db               # Banco SQLite de memória do agente
│
└── spec/                       # Documentação
    ├── prd-agente-reuniao.md
    └── arquitetura-zero.md     # Este arquivo
```

---

## 4. Pilar 1: Núcleo do Agente

### 4.1 `agent/context.py` — Memória de Conversa

O problema central de qualquer agente é: **ele esquece tudo** a cada chamada de API. A solução é manter um histórico local e passá-lo de forma comprimida para o modelo.

```
chat_id: 123456
  └── histórico:
        [turn 1] usuário: "/rpg_resumo"
        [turn 1] bot: "Aqui está a crônica..."
        [turn 2] usuário: "Refaça com mais drama"
        [turn 2] bot: "..."
```

**Estratégia de Economia de Tokens:**
- Histórico guardado **localmente em SQLite** (não na API)
- Apenas as **últimas N interações** são injetadas no prompt
- Turnos antigos são **comprimidos em um resumo** (via chamada barata ao Gemini Flash Lite)
- Contexto injetado somente quando o módulo solicita

```python
# agent/context.py (estrutura esperada)
class ContextManager:
    MAX_TURNS_VIVOS = 5        # Turnos recentes injetados diretamente
    MAX_TURNS_ARQUIVO = 50     # Turnos mais antigos viram resumo comprimido

    def get_context(self, chat_id: int) -> str:
        """Retorna o contexto pronto para injetar no prompt."""

    def add_turn(self, chat_id: int, role: str, content: str):
        """Salva um turno no banco."""

    async def compress_old_turns(self, chat_id: int):
        """Comprime turnos antigos em um parágrafo de resumo."""
```

### 4.2 `agent/token_manager.py` — Orçamento de Tokens

O Gemini gratuito tem cotas diárias rígidas. O `TokenManager` garante que o bot **nunca as estoure** e sempre **priorize o que gasta menos**.

```python
# agent/token_manager.py (estrutura esperada)
class TokenManager:
    # Estimativa: 1 token ≈ 4 caracteres
    LIMITE_ENTRADA_PADRAO = 30_000   # tokens por chamada
    LIMITE_DIARIO = 1_000_000        # tokens por dia (free tier)

    def estimar(self, texto: str) -> int:
        """Estimativa rápida de tokens sem chamar a API."""
        return len(texto) // 4

    def verificar_orcamento(self, texto: str):
        """Lança exceção se o texto exceder o limite configurado."""

    def registrar_uso(self, tokens_entrada: int, tokens_saida: int):
        """Persiste o uso do dia no SQLite para controle."""

    def relatorio(self) -> str:
        """Retorna string com uso do dia para o /status."""
```

**Regra de Ouro:** Todo módulo que chama o Gemini deve passar pelo `TokenManager` antes de enviar o prompt. Se exceder o orçamento, o bot responde com aviso amigável em vez de desperdiçar a cota.

### 4.3 `agent/prompt_registry.py` — Repositório de Prompts

Prompts espalhados pelo código são impossíveis de manter. O `PromptRegistry` centraliza tudo:

```python
# agent/prompt_registry.py (estrutura esperada)
PROMPTS = {
    "rpg.cronica": {
        "version": "2.1",
        "model_hint": "gemini-2.5-flash-lite",   # modelo mais barato que atende
        "max_input_tokens": 25_000,
        "template": """
            Atue como 'Narrador de RPG'...
            --- Contexto da sessão anterior ---
            {contexto}
            --- Transcrição ---
            {transcricao}
        """
    },
    "rpg.transcricao": {
        "version": "1.0",
        "model_hint": "gemini-2.5-flash-lite",
        "template": "Por favor, transcreva este áudio fielmente."
    },
    "compress.historico": {
        "version": "1.0",
        "model_hint": "gemini-2.0-flash-lite",   # o mais barato possível
        "template": "Resuma em 3 frases o histórico abaixo:\n{historico}"
    }
}

def get(key: str) -> dict:
    return PROMPTS[key]
```

**Benefício:** Para mudar o estilo da crônica, você edita **um único lugar**. O número da versão facilita saber se o prompt mudou desde o último deploy.

---

## 5. Pilar 2: Módulos de Comandos

### 5.1 Como um Módulo é Estruturado

Cada módulo é um arquivo Python simples. O padrão é:

```python
# bot/modules/rpg.py
from services.gemini_service import GeminiService
from services.drive_service  import DriveService
from services.pdf_service    import PdfService
from agent.context           import ContextManager
from agent.token_manager     import TokenManager
from agent.prompt_registry   import get as get_prompt
from config                  import logger

# Instâncias compartilhadas (criadas uma vez, reaproveitadas)
_gemini  = GeminiService()
_drive   = DriveService()
_pdf     = PdfService()
_ctx     = ContextManager()
_tokens  = TokenManager()

async def rpg_transcrever(update, context):
    """
    /rpg_transcrever
    Encontra o áudio mais recente no Drive e gera a transcrição.
    """
    ...

async def rpg_resumo(update, context):
    """
    /rpg_resumo
    Lê a transcrição mais recente e gera a Crônica Épica em PDF.
    """
    ...
```

### 5.2 Catálogo de Módulos Planejados

| Módulo | Comandos | Descrição |
|---|---|---|
| `core.py` | `/start`, `/ajuda`, `/status`, `/memoria` | Comandos universais do agente |
| `rpg.py` | `/rpg_transcrever`, `/rpg_resumo` | Crônicas de sessões de RPG |
| `reuniao.py` *(futuro)* | `/reuniao_resumo`, `/reuniao_ata` | Atas de reuniões corporativas |
| `estudo.py` *(futuro)* | `/estudo_resumo`, `/estudo_quiz` | Resumo de aulas e flashcards |
| `doc.py` *(futuro)* | `/doc_resumir`, `/doc_perguntar` | Chat com documentos (PDF/Drive) |

### 5.3 `bot/modules/core.py` — Comandos Universais

```
/start     → Boas-vindas e lista de módulos disponíveis
/ajuda     → Explica todos os comandos (gerado dinamicamente pelo registry)
/status    → RAM usada, tokens consumidos hoje, módulos ativos
/memoria   → Mostra/apaga o contexto guardado do chat atual
```

---

## 6. Pilar 3: Serviços

### 6.1 `services/gemini_service.py`

A camada mais crítica. Centraliza **todas** as chamadas ao Gemini com:

| Funcionalidade | Detalhe |
|---|---|
| **Retry com backoff** | 429 / 503 → espera exponencial, detecta cota esgotada (fail-fast) |
| **Seleção de modelo** | Cada prompt declara o `model_hint` — o serviço usa o mais barato adequado |
| **RAG local** | Textos > 15.000 chars são chunkeados + filtrados por similaridade de cosseno antes de enviar |
| **Transcrição de áudio** | Upload via File API + polling de estado ACTIVE + deletar após uso |
| **Embeddings** | `gemini-embedding-001` para busca semântica no RAG |

### 6.2 `services/memory_service.py` — Persistência em SQLite

```
data/memory.db
├── tabela: context_turns
│    └── chat_id | role | content | timestamp | is_compressed
└── tabela: token_usage
     └── date | input_tokens | output_tokens | model
```

SQLite é suficiente: é embutido no Python, não precisa de servidor, e aguenta centenas de chats sem problema.

### 6.3 `services/drive_service.py`

| Método | Detalhe |
|---|---|
| `encontrar_arquivo(mime_type)` | Busca genérica por tipo MIME |
| `fazer_download(file_id, path)` | Streaming em chunks de 1MB (RAM segura) |
| `fazer_upload(path, nome, mime)` | Upload com metadados e pasta de destino |
| `_obter_service()` | OAuth2 lazy: usa `token.json` se existir, senão abre navegador |

---

## 7. Fluxo Completo de uma Chamada com Contexto

```
1. Usuário: /rpg_resumo
         │
2. middleware.py verifica autenticação e rate limit pessoal
         │
3. rpg.py (handler)
         │
         ├─ drive: baixa .txt da transcrição
         │
         ├─ token_manager: estima tokens do .txt
         │     ├─ SE > limite → gemini_service: RAG reduz para top-K chunks
         │     └─ SE ok → usa texto completo
         │
         ├─ context_manager: busca contexto da conversa (se /rpg_resumo foi usado antes)
         │
         ├─ prompt_registry: monta prompt com template + contexto + transcrição
         │
         ├─ token_manager: verifica orçamento final antes de enviar
         │
         ├─ gemini_service: chama Gemini, recebe Markdown
         │
         ├─ pdf_service: converte Markdown → PDF
         │
         ├─ drive: faz upload do PDF
         │
         ├─ context_manager: salva este turno no histórico
         │
         └─ telegram: envia PDF ao usuário
```

---

## 8. Economia de Tokens — Estratégias

| Estratégia | Onde | Economia Estimada |
|---|---|---|
| **RAG local** | `gemini_service.py` | 60–80% em transcrições longas |
| **Histórico comprimido** | `context.py` | 70% no contexto de conv. longa |
| **model_hint (modelo mais barato)** | `prompt_registry.py` | 5–10x em custo por chamada |
| **Estimativa sem API** | `token_manager.py` | 100% nas verificações de orçamento |
| **Fail-fast na cota esgotada** | `gemini_service.py` | Evita retries inúteis |
| **Cache de embeddings** | `memory_service.py` *(futuro)* | Elimina re-embedding de chunks iguais |

---

## 9. `bot/middleware.py` — Proteções do Bot

```python
# Funcionalidades planejadas:
# 1. Whitelist de chat_ids autorizados (só você e quem você aprovar)
# 2. Rate limit pessoal: max N comandos por minuto por usuário
# 3. Log de todas as chamadas (quem, quando, qual comando)
# 4. Captura global de exceções não tratadas → notifica o admin
```

---

## 10. Configuração de Ambiente (`.env`)

```dotenv
# Telegram
TELEGRAM_TOKEN=seu_token_aqui
ALLOWED_CHAT_IDS=123456789,987654321   # IDs autorizados (separados por vírgula)

# Google Gemini
GEMINI_API_KEY=sua_chave_aqui

# Google Drive (OAuth2)
DRIVE_CREDENTIALS_PATH=client_secret.json
DRIVE_FOLDER_ID=id_da_pasta_no_drive

# Agente
MAX_TOKENS_POR_CHAMADA=30000
MAX_TOKENS_DIARIO=1000000
CONTEXTO_MAX_TURNS=5
```

---

## 11. Dependências (`requirements.txt`)

```
python-telegram-bot==21.*
google-genai>=1.0
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
fpdf2
python-dotenv
httpx
```

> Nenhuma dependência de frameworks de agente externo (LangChain, etc.). Tudo construído do zero para máximo controle e mínimo overhead.

---

## 12. Deploy no Servidor Linux

### 12.1 Instalação

```bash
git clone https://github.com/seu-user/agente-reuniao.git
cd agente-reuniao
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env
```

### 12.2 Serviço `systemd`

```ini
# /etc/systemd/system/oraculo-de-mesa.service
[Unit]
Description=Oráculo de Mesa — Agente Pessoal IA
After=network.target

[Service]
Type=simple
User=seu_usuario
WorkingDirectory=/caminho/agente-reuniao
ExecStart=/caminho/agente-reuniao/venv/bin/python main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable oraculo-de-mesa
sudo systemctl start oraculo-de-mesa
sudo journalctl -u oraculo-de-mesa -f   # ver logs ao vivo
```

### 12.3 OAuth2 Drive no Servidor (Sem Navegador)

```bash
# Na sua máquina LOCAL:
python main.py   # autoriza no navegador, gera token.json

# Transfere para o servidor:
scp token.json usuario@servidor:/caminho/agente-reuniao/
```

### 12.4 Atualizar

```bash
cd /caminho/agente-reuniao
git pull
sudo systemctl restart oraculo-de-mesa
```

---

## 13. Adicionando um Novo Módulo — Passo a Passo

**Exemplo: `/estudo_resumo`**

**Passo 1** — Criar `bot/modules/estudo.py`:
```python
from services.gemini_service import GeminiService
from agent.prompt_registry   import get as get_prompt

_gemini = GeminiService()

async def estudo_resumo(update, context):
    """Resumo de aula ou documento enviado como arquivo."""
    ...
```

**Passo 2** — Adicionar o prompt em `agent/prompt_registry.py`:
```python
"estudo.resumo": {
    "version": "1.0",
    "model_hint": "gemini-2.0-flash-lite",
    "template": "Resuma o conteúdo abaixo em tópicos para estudo:\n{conteudo}"
}
```

**Passo 3** — Registrar em `bot/registry.py`:
```python
from bot.modules import estudo
app.add_handler(CommandHandler("estudo_resumo", estudo.estudo_resumo))
```

**Passo 4** — Reiniciar o serviço no servidor.

Nenhum outro arquivo precisa ser alterado.

---

## 14. Regras de Ouro do Projeto

| Regra | Motivo |
|---|---|
| Nunca `file.read()` em arquivos > 10MB | RAM do servidor |
| Sempre `try/finally` para limpar temp files | Evitar lotar o disco |
| Toda chamada ao Gemini passa pelo `TokenManager` | Não estourar a cota gratuita |
| Prompts vivem apenas no `prompt_registry.py` | Fácil de manter e versionar |
| Contexto injetado só quando o módulo pede | Não desperdiçar tokens em comandos simples |
| Módulos não conhecem detalhes de implementação dos serviços | Desacoplamento |
| Credenciais nunca no git | Segurança |
