# Agente Reunião (Oráculo de Mesa)

Este é um bot de Telegram assíncrono projetado para funcionar em servidores com baixa memória RAM (< 1GB). Ele faz download de ficheiros de áudio pesados do Google Drive usando streams/chunks, utiliza a File API do Gemini (Google) para processamento em nuvem, transcreve a sessão e gera uma "Crónica Épica" de RPG em formato PDF de forma nativa e gratuita.

O sistema inclui uma camada de **RAG (Retrieval-Augmented Generation)** para processar transcrições de longa duração (mais de 1 hora), selecionando semanticamente os trechos mais relevantes para garantir que o limite de tokens não seja excedido e que a qualidade da crônica seja mantida.

## Pré-requisitos
- Python 3.10+
- Conta no Google Cloud com a API do Google Drive ativada
- API Key do Gemini (Google AI Studio)
- Bot criado no BotFather (Telegram) com o respetivo Token

## Instalação e Execução

1. **Configurar o ambiente virtual (venv):**
```bash
python -m venv venv
```

2. **Ativar o ambiente virtual:**
No Windows:
```bash
.\venv\Scripts\activate
```
No Linux/Mac:
```bash
source venv/bin/activate
```

3. **Instalar as dependências:**
```bash
pip install -r requirements.txt
```

4. **Configurar o ficheiro `.env`:**
Copie o ficheiro `.env.example` para `.env` e preencha as suas chaves.

5. **Correr o bot:**
```bash
python main.py
```

## Como configurar as Credenciais do Google Drive (OAuth2)

1. Vá à [Google Cloud Console](https://console.cloud.google.com/).
2. Crie um novo projeto ou selecione um existente.
3. No menu de navegação, vá a **APIs & Services** > **Library**.
4. Procure por **Google Drive API** e clique em **Enable** (Ativar).
5. Vá a **APIs & Services** > **OAuth consent screen** e configure como "External" (ou Internal se tiver Workspace). Adicione o seu email como "Test User".
6. Vá a **APIs & Services** > **Credentials**.
7. Clique em **Create Credentials** > **OAuth client ID**.
8. Escolha **Desktop App**, dê um nome e clique em **Create**.
9. Descarregue o ficheiro JSON, renomeie-o para `client_secret.json` (ou o nome configurado no `.env`) e coloque-o na raiz do projeto.
10. Na primeira execução, o bot abrirá uma janela no seu navegador para autorizar o acesso ao Drive. O token será guardado em `token.json` para uso futuro.

## Como usar
Após iniciar o bot, vá ao seu Telegram e envie a mensagem `/rpg_resumo` para que ele procure o áudio mais recente no Drive, processe as informações e lhe devolva o PDF final com a crónica da sessão!

