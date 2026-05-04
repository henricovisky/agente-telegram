# Diretrizes de Gestão de Servidor e Rede (Oráculo)

Este documento define como o Agente Oráculo deve se comportar ao executar comandos no servidor e gerenciar a rede Tailscale.

## 1. Princípios de Segurança
- **Mínimo Privilégio**: Use `sudo` apenas quando estritamente necessário.
- **Validação de Comando**: Antes de executar, explique brevemente o que o comando faz.
- **Prevenção de Danos**: Nunca execute `rm -rf /` ou comandos que possam desativar o acesso SSH/Tailscale sem um aviso explícito.

## 2. Comandos de Rede (Tailscale)
- **Status da Rede**: Use `tailscale status` para ver dispositivos conectados.
- **Verificar IP**: Use `tailscale ip -4`.
- **Diagnóstico**: `tailscale ping <device-ip>` para verificar conectividade.
- **Localização**: Dispositivos conhecidos devem ser referenciados pelo nome DNS da Tailscale se possível.

## 3. Gestão de Serviços (Systemd)
- **Status do Bot**: `systemctl status agente-telegram` (ou nome do serviço).
- **Restart**: `sudo systemctl restart agente-telegram`.
- **Logs**: `journalctl -u agente-telegram -n 50 --no-pager`.

## 4. Modificações no Servidor
- **Atualização de Código**: Ao usar `/update` ou git, verifique sempre o `git status` e `git branch` antes.
- **Permissões**: Se encontrar erro de permissão, sugira o uso de `chmod` ou `chown` apenas nas pastas do projeto.

## 5. Fluxo de Trabalho no Telegram
1. O usuário chama `/server exec <comando>` ou comandos específicos como `/server net`.
2. O bot (via `terminal_service`) executa o comando.
3. Se o Agente estiver processando uma tarefa complexa (ex: "ajuste as permissões e reinicie"), ele deve seguir esta ordem:
   - Analisar a necessidade.
   - Propor os comandos.
   - Executar via ferramenta interna (se disponível) ou instruir o usuário a usar o comando de terminal do bot.
