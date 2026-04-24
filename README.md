# Henricovisky — Agente IA Pessoal no Telegram

Bot de IA pessoal que roda no seu próprio servidor 24/7. Funciona como um assistente inteligente via Telegram: você envia um comando, ele pensa com o **Gemini** e executa automações reais — transcrição de áudios, geração de PDFs, acesso ao Google Drive — sem custos de assinatura e sem limites de plataforma.

> Arquitetura modular: cada novo comando é um arquivo novo em `bot/modules/`. O agente possui **Poderes de Terminal**, permitindo executar comandos bash para gerenciar o servidor e arquivos via chat.

---

## Módulos disponíveis

| Comando | Descrição |
|---|---|
| `/start` | Boas-vindas e lista de módulos |
| `/ajuda` | Todos os comandos disponíveis |
| `/status` | Tokens Gemini usados hoje |
| `/status_server` | Métricas detalhadas: CPU, RAM, Disco, Rede e Sistema |
| `/update` | Atualiza o bot via GitHub + reinicia |
| `/memoria` | Histórico de conversa do chat |
| `/memoria_limpar` | Apaga o histórico |
| `/rpg_transcrever` | Transcreve o áudio de RPG mais recente do Drive |
| `/rpg_resumo` | Gera a Crônica Épica em PDF a partir da transcrição |
| `Texto Livre` | Conversa com o agente (com **Poderes de Terminal**, ferramentas e **Multi-model Fallback**) |

---

## Resiliência e Inteligência

O Henricovisky foi projetado para ser imparável. Se o modelo principal falhar ou atingir o limite de cota, ele utiliza uma estratégia de **Failover Automático**:

1.  **Modelo Primário:** `gemini-3-flash-preview` (Velocidade e raciocínio avançado)
2.  **Fallback 1:** `gemini-3.1-flash-lite` (Eficiência e novos recursos)
3.  **Fallback 2:** `gemma-4-26b` (Poderoso modelo open-source via API)
4.  **Fallback 3:** `gemma-3-27b` / `gemma-3-4b` (Resiliência total)

> **Nota:** O agente detecta erros `429 (Resource Exhausted)` e troca de modelo em tempo real sem interromper a experiência do usuário.

---

## Funcionalidades Futuras (Sugestões de Especialista)

Como arquiteto do sistema, estas são as próximas evoluções recomendadas para transformar este bot em uma central de comando definitiva:

- [ ] **Visão Computacional:** Capacidade de analisar prints de tela do servidor ou logs em imagem para diagnóstico rápido.
- [ ] **Web Search Integrado:** Permitir que o agente pesquise documentações técnicas atualizadas no Google Search antes de sugerir comandos de terminal.
- [ ] **Monitoramento Ativo (Watcher):** Um processo de fundo que avisa no Telegram se o uso de CPU passar de 90% ou se um serviço (ex: Docker) cair.
- [ ] **Agendamento de Tarefas:** "Henricovisky, faça um backup do banco de dados todo domingo às 3 da manhã".
- [ ] **Interface Web de Monitoramento:** Um mini-dashboard (usando Next.js ou Streamlit) para visualizar o uso de tokens e status do servidor graficamente.

---

## Pré-requisitos

- VPS Linux (Ubuntu 22.04+) com mínimo 1 GB RAM
- Python 3.10+
- Conta Google Cloud com **Drive API** ativada
- **API Key do Gemini** (Google AI Studio — gratuito)
- **Token do Bot Telegram** (criado no BotFather)

---

## Deploy no Servidor

### 1. Gerar o token OAuth2 do Drive (na sua máquina local)

Antes de ir ao servidor, autorize o acesso ao Google Drive uma única vez na sua máquina:

```bash
git clone https://github.com/henricovisky/agente-telegram.git
cd agente-telegram
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
python main.py   # um navegador vai abrir → autorize → token.json é gerado
# Ctrl+C para parar após o token ser gerado
```

### 2. Transferir arquivos para o servidor

```bash
scp setup_server.sh    usuario@servidor:/tmp/
scp client_secret.json usuario@servidor:/tmp/
scp token.json         usuario@servidor:/tmp/
```

### 3. Rodar o script de instalação no servidor

```bash
ssh usuario@servidor
bash /tmp/setup_server.sh
```

O script faz automaticamente:
- Instala Python 3, Git e dependências do sistema
- Clona o repositório em `/opt/henricovisky`
- Cria o ambiente virtual e instala os pacotes
- Cria o arquivo `.env` a partir do exemplo
- Registra o serviço `systemd` com reinício automático

### 4. Configurar as credenciais

```bash
nano /opt/henricovisky/.env
```

Preencha:
```dotenv
TELEGRAM_TOKEN=seu_token_do_botfather
GEMINI_API_KEY=sua_chave_do_google_ai_studio
DRIVE_FOLDER_ID=id_da_pasta_no_drive
ALLOWED_CHAT_IDS=seu_chat_id_do_telegram
```

> Seu chat ID pode ser obtido falando com `@userinfobot` no Telegram.

### 5. Mover as credenciais OAuth2

```bash
mv /tmp/client_secret.json /opt/henricovisky/
mv /tmp/token.json         /opt/henricovisky/
```

### 6. Iniciar o bot

```bash
sudo systemctl start henricovisky
sudo journalctl -u henricovisky -f   # ver logs ao vivo
```

O bot sobe automaticamente com o servidor e se reinicia em caso de falha.

---

## Uso do `start.sh` (script inteligente)

O `start.sh` verifica o ambiente antes de iniciar. Pode ser usado tanto no servidor quanto localmente:

```bash
bash start.sh
```

O que ele verifica:
- ✔ Python 3 instalado
- ✔ `venv/` existe (cria se não existir)
- ✔ Dependências do `requirements.txt` instaladas (instala se não estiver)
- ✔ `.env` preenchido (não apenas o exemplo)
- ⚠ `token.json` e `client_secret.json` presentes
- ✔ Pasta `data/` criada

Se tudo estiver OK, inicia o bot diretamente.

---

## Atualizar o bot

Via Telegram, basta enviar:
```
/update
```

O bot faz `git pull`, `pip install -r requirements.txt` e reinicia o processo automaticamente.

---

## Adicionar um novo comando

1. Criar `bot/modules/meu_modulo.py` com a função handler
2. Registrar em `bot/registry.py`:
   ```python
   from bot.modules import meu_modulo
   app.add_handler(CommandHandler("meu_comando", autorizados_apenas(meu_modulo.handler)))
   ```
3. Enviar `/update` no Telegram

---

## Estrutura do Projeto

```
agente-telegram/
├── main.py                    # Ponto de entrada
├── config.py                  # Variáveis de ambiente
├── start.sh                   # Script inteligente de inicialização
├── setup_server.sh            # Instalação completa no servidor
│
├── agent/                     # Núcleo do agente
│   ├── context.py             # Memória de conversa por chat
│   ├── token_manager.py       # Orçamento e rastreamento de tokens
│   └── prompt_registry.py     # Repositório central de prompts
│
├── bot/
│   ├── registry.py            # Registro central de comandos
│   ├── middleware.py          # Autenticação e controle de acesso
│   └── modules/
│       ├── core.py            # Comandos base (/start, /status, /update...)
│       ├── rpg.py             # Módulo RPG
│       └── admin.py           # /update
│
└── services/
    ├── gemini_service.py      # Gemini: transcrição, geração, RAG, **Function Calling**
    ├── terminal_service.py    # Execução de comandos bash segura
    ├── drive_service.py       # Google Drive: upload, download, busca
    ├── pdf_service.py         # Markdown → PDF (fpdf2)
    └── memory_service.py      # SQLite: rastreamento de tokens
```

---

## Segurança

- Credenciais nunca versionadas (`.gitignore` cobre `.env`, `token.json`, `client_secret.json`)
- Acesso restrito por `ALLOWED_CHAT_IDS` — só você (e quem você listar) pode usar o bot
- Servidor com `Restart=always` no systemd — resiliente a crashes
