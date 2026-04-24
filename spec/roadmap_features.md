# 🚀 Roadmap de Funcionalidades — Henricovisky Bot

---

## 🧠 1. Inteligência & Contexto

| Ideia | Descrição | Complexidade |
|---|---|---|
| **Memória de longo prazo (RAG pessoal)** | ✅ Concluído: Armazenamento de fatos em SQLite com embeddings e busca semântica. | Alta |
| **Personas intercambiáveis** | ✅ Concluído: Sistema de registro e troca de personas (/persona) implementado. | Média |
| **Resumo automático da conversa** | ✅ Concluído: Compressão automática de histórico quando excede 16 mensagens. | Baixa |
| **Modo planejador (ReAct)** | ✅ Concluído: O agente agora planeja passos e exibe o raciocínio explicitamente em tarefas complexas. | Alta |

---

## 📋 2. Produtividade Pessoal

| Ideia | Descrição | Complexidade |
|---|---|---|
| **Lembretes e alarmes** | `/lembrete 20min reunião com o João` — usa APScheduler para enfileirar notificações agendadas. | Média |
| **Resumo diário automático** | Todo dia às 7h, envia um briefing gerado pelo Gemini com: clima, agenda do Google Calendar, lembretes pendentes. | Alta |
| **Notas rápidas** | `/nota [texto]` salva em SQLite; `/notas` lista todas; `/nota_apagar [id]` remove. O agente pode buscar nas notas via texto livre. | Baixa |
| **Leitor de e-mails** | Integra Gmail API: `/emails` mostra os últimos 5 não lidos com resumo do Gemini. | Alta |
| **Rastreador de tarefas (To-Do)** | `/task add`, `/task list`, `/task done [id]` — simples, sem depência externa, tudo em SQLite local. | Baixa |

---

## 🎙️ 3. Multimédia & Arquivos

| Ideia | Descrição | Complexidade |
|---|---|---|
| **Transcrição de qualquer áudio do Telegram** | Receber um áudio/voice note diretamente no chat e transcrever na hora (sem precisar estar no Drive). | Baixa |
| **Análise de imagens** | Receber foto e perguntar sobre ela (ex: "o que está escrito nessa placa?", "quem é esse personagem?") usando Gemini Vision. | Baixa |
| **Resumo de PDF/documento** | Enviar um PDF pelo Telegram e o bot devolve um resumo executivo gerado pelo Gemini. | Média |
| **Geração de imagens** | `/imagine [descrição]` — usa Imagen (Google) ou Stable Diffusion local para gerar uma imagem e enviar no chat. | Alta |
| **Narração de texto** | `/falar [texto]` — converte texto em áudio MP3 com TTS e envia como mensagem de voz. | Média |

---

## 📊 4. Monitoramento & Alertas

| Ideia | Descrição | Complexidade |
|---|---|---|
| **Alertas proativos de servidor** | ✅ Concluído: Job verifica CPU, RAM e Disco e alerta no Telegram. | Baixa |
| **Monitor de serviços** | ✅ Concluído: Verifica status do serviço systemd `henricovisky`. | Baixa |
| **Tail de logs em tempo real** | ✅ Concluído: `/logs [serviço]` exibe últimas 20 linhas via journalctl. | Baixa |

---

## 🔧 5. Administração do Sistema

| Ideia | Descrição | Complexidade |
|---|---|---|
| **Execução de scripts agendados** | `/run [script]` — executa um script Python/bash pré-autorizado da lista de scripts seguros. | Média |
| **Backup automático via chat** | `/backup db` — dispara o backup do banco de dados e envia o arquivo compactado ou um link no Drive. | Média |
| **Gerenciador de processos** | `/ps` lista processos pesados; `/kill [pid]` termina processo (com confirmação de segurança). | Média |
| **Deploy de projetos** | `/deploy [projeto]` — faz git pull + restart de qualquer outro serviço cadastrado, não só o bot. | Alta |
| **Tunnel SSH temporário** | Abre um túnel ngrok/cloudflare temporário e envia a URL, útil para acessar serviços locais externamente. | Alta |

---

## 🤝 6. Integração com Sistemas Externos

| Ideia | Descrição | Complexidade |
|---|---|---|
| **Integração com Zeev** | Consultar status de processos, instâncias abertas, ou disparar workflows via API do Zeev. | Alta |
| **Integração com Mega ERP** | Consultar lançamentos, saldos ou relatórios financeiros via API do Mega. | Alta |
| **Consulta ao DW via linguagem natural** | "Quais foram as vendas do mês passado?" → Gemini gera o SQL → executa no DW → devolve o resultado formatado. | Alta |
| **Notificações de Pull Request** | Webhook do GitHub → bot avisa quando um PR é aberto/mergeado em repositórios de interesse. | Média |
| **Integração com Notion/Obsidian** | `/nota_notion [texto]` cria uma página no Notion; ou sincroniza notas com vault do Obsidian via Drive. | Alta |

---

## 🎲 7. Expansão do Módulo RPG

| Ideia | Descrição | Complexidade |
|---|---|---|
| **Rolagem de dados inteligente** | `/rolar 2d6+3 ataque` — simula dados e descreve o resultado com narração épica do Gemini. | Baixa |
| **Ficha de personagem** | Salvar e consultar fichas de D&D 5e em formato estruturado; o agente consulta a ficha para contextualizar rolagens. | Média |
| **Gerador de NPCs** | `/npc` — gera um NPC completo (nome, raça, motivação, segredo) com backstory narrativo. | Baixa |
| **Gerador de encontros** | `/encontro [CR] [terreno]` — sugere um encontro balanceado para o grupo com descrição de ambiente. | Baixa |
| **Histórico de campanhas** | Banco de dados de sessões anteriores; o narrador pode perguntar "o que aconteceu na sessão 3?" | Média |

---

## 🔐 8. Segurança & Robustez

| Ideia | Descrição | Complexidade |
|---|---|---|
| **Rate limiting por usuário** | Limitar N mensagens por minuto por chat_id para evitar abuso ou loops de tokens. | Baixa |
| **Modo manutenção** | `/manutencao on/off` — pausa o atendimento a novos usuários enquanto faz updates críticos. | Baixa |
| **Auditoria de comandos** | Log estruturado de quem executou qual comando, quando, com qual parâmetro — em SQLite local. | Baixa |
| **Backup automático do `.env` e credenciais** | Envia cópia criptografada para o Drive semanalmente. | Média |

---

> **Legenda de complexidade:**
> - 🟢 **Baixa** — 1–2h, menos de 100 linhas de código
> - 🟡 **Média** — meio dia, pode precisar de nova dependência
> - 🔴 **Alta** — 1–3 dias, arquitetura nova ou integração externa complexa
