PRD e System Spec: Projeto "Oráculo de Mesa" (RPG Automático)

1. Visão Geral (O Problema e a Solução)

O Problema: Ferramentas No-Code como o n8n engolem demasiada memória RAM ao manipular ficheiros de áudio pesados (150MB+), causando o colapso de servidores pequenos (VPS de 1GB de RAM). Além disso, dependem de APIs limitadas de terceiros para gerar PDFs.
A Solução: Um bot Telegram em Python puro e assíncrono. O script atua como um "cano de esgoto de luxo", fazendo streaming do áudio do Google Drive diretamente para a Google File API (Gemini), sem nunca carregar o ficheiro completo para a memória RAM. O PDF é gerado localmente de forma vitalícia e gratuita.

2. Requisitos do Produto (PRD)

Trigger: O utilizador envia o comando /rpg_resumo no Telegram.

Input: O bot deve procurar no Google Drive o ficheiro de áudio mais recente.

Processamento 1 (Transcrição): Enviar o áudio para o modelo gemini-1.5-flash para transcrição bruta. Guardar o resultado num ficheiro TXT e fazer upload para o Drive.

Processamento 2 (Narrativa): Enviar a transcrição para o gemini-1.5-pro com um prompt focado em transformar a sessão numa Crónica Épica de RPG.

Output Local: Converter o texto Markdown da Crónica num ficheiro PDF localmente.

Entrega: Fazer upload do PDF para o Google Drive e enviar o documento final de volta para o utilizador no Telegram.

3. Especificações Técnicas (System Spec)

Linguagem: Python 3.10+

Framework Bot: python-telegram-bot (Versão 20+, usando asyncio).

Memória RAM: Estritamente otimizado para < 100MB de consumo. PROIBIDO usar file.read() em ficheiros grandes.

Integração Google Drive: google-api-python-client. O download deve ser feito em pedaços (chunks) usando MediaIoBaseDownload ou streaming direto.

Integração Gemini: Usar o SDK oficial google-generativeai. Crucial: Para ficheiros > 20MB, usar obrigatoriamente a genai.upload_file() (File API) para processamento assíncrono, aguardando o estado ACTIVE antes de chamar o modelo.

Geração de PDF: Usar fpdf2 ou markdown-pdf para processar a resposta do Gemini e gerar o ficheiro local sem APIs externas.

Deploy: Deve conter um requirements.txt e um ficheiro .env para as credenciais (Telegram Token, Gemini API Key, Drive Credentials path).

4. O PROMPT MESTRE (Para o Agente Antigravity)

Instrução para o Agente: Age como um Engenheiro Python Sénior obcecado por otimização de memória. Lê os requisitos acima e escreve a aplicação completa num único ficheiro principal (main.py), ou dividida de forma modular se preferires, desde que o código esteja impecável.

Regras de Ouro na Geração do Código:

O servidor tem apenas 1GB de RAM. NUNCA leias o ficheiro de áudio de 100MB+ para a RAM de uma só vez. Usa streams ou generators.

Quando fizeres o download do Drive, descarrega para o disco local em blocos (chunks).

Quando enviares para o Gemini, usa o genai.upload_file(path_local) da File API do Gemini. Isto envia do disco para a nuvem sem rebentar com a RAM. Aguarda que o ficheiro mude do estado PROCESSING para ACTIVE num loop de verificação antes de pedir a transcrição.

Depois de o Gemini Flash devolver a transcrição bruta, chama o Gemini Pro com o seguinte prompt base: "És um Mestre de RPG veterano. Pega no seguinte resumo bruto de uma sessão e transforma-o numa crónica épica, formatada em Markdown, focando-te nas ações dos jogadores, itens encontrados e ganchos da história. Resumo bruto: {texto}".

Cria o PDF nativamente em Python usando fpdf2 (com suporte a UTF-8/Unicode para evitar erros em caracteres portugueses).

Depois do upload do PDF e do TXT para o Drive e do envio pelo Telegram, o script TEM de apagar os ficheiros temporários locais (.mp3/.wav, .txt, .pdf) usando os.remove() para não lotar o disco de 45GB.

Escreve código limpo, com controlo de erros (try/except) e logs (logging) para facilitar a depuração.

Gera o código Python, o requirements.txt e explica passo-a-passo como devo configurar as credenciais do Google Cloud (Service Account).

use gitignore e venv