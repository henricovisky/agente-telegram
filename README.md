# Agente Reunião (Oráculo de Mesa)

Este é um bot de Telegram assíncrono projetado para funcionar em servidores com baixa memória RAM (< 1GB). Ele faz download de ficheiros de áudio pesados do Google Drive usando streams/chunks, utiliza a File API do Gemini (Google) para processamento em nuvem, transcreve a sessão e gera uma "Crónica Épica" de RPG em formato PDF de forma nativa e gratuita.

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
Copie o ficheiro `.env.example` para `.env` e preencha as suas chaves e o caminho para o ficheiro `credentials.json` do Google Drive.

5. **Correr o bot:**
```bash
python main.py
```

## Como configurar as Credenciais do Google Cloud (Service Account)

1. Vá à [Google Cloud Console](https://console.cloud.google.com/).
2. Crie um novo projeto ou selecione um existente.
3. No menu de navegação, vá a **APIs & Services** > **Library**.
4. Procure por **Google Drive API** e clique em **Enable** (Ativar).
5. Vá a **APIs & Services** > **Credentials**.
6. Clique em **Create Credentials** no topo e escolha **Service Account**.
7. Preencha o nome da conta de serviço e clique em **Create and Continue**, depois conclua.
8. Na lista de Service Accounts, clique no email da conta acabada de criar.
9. Vá ao separador **Keys**, clique em **Add Key** > **Create new key**. Escolha **JSON** e clique em **Create**.
10. Um ficheiro `.json` será descarregado para o seu computador. Renomeie-o para `credentials.json` e coloque-o na raiz do seu projeto.
11. **IMPORTANTE:** Vá à pasta do seu Google Drive onde os ficheiros de áudio estão guardados, clique em "Partilhar" e adicione o endereço de e-mail da sua Service Account (ex: `exemplo@projeto.iam.gserviceaccount.com`) com permissões de Leitor ou Editor. Copie o ID da pasta do link para usar no seu ficheiro `.env`.

## Como usar
Após iniciar o bot, vá ao seu Telegram e envie a mensagem `/rpg_resumo` para que ele procure o áudio mais recente no Drive, processe as informações e lhe devolva o PDF final com a crónica da sessão!
