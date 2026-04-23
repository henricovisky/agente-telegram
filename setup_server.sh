#!/usr/bin/env bash
# =============================================================================
# setup_server.sh — Instala e configura o Oráculo de Mesa no servidor Linux
# Testado em: Ubuntu 22.04 LTS
# Uso: bash setup_server.sh
# =============================================================================
set -e  # Aborta se qualquer comando falhar

# --------------------------------------------------------------------------- #
# CONFIGURAÇÕES — edite antes de rodar
# --------------------------------------------------------------------------- #
REPO_URL="https://github.com/henricovisky/agente-reuni-o.git"  # URL do seu repo
APP_DIR="/opt/oraculo-de-mesa"                                  # Pasta de instalação
SERVICE_NAME="oraculo-de-mesa"
SERVICE_USER="$(whoami)"                                        # Usuário que vai rodar o bot
# --------------------------------------------------------------------------- #

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

step() { echo -e "\n${GREEN}▶ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }

# --------------------------------------------------------------------------- #
# 1. Dependências do sistema
# --------------------------------------------------------------------------- #
step "Atualizando pacotes do sistema..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv git

# --------------------------------------------------------------------------- #
# 2. Clonar ou atualizar o repositório
# --------------------------------------------------------------------------- #
if [ -d "$APP_DIR/.git" ]; then
    step "Repositório já existe — fazendo git pull..."
    cd "$APP_DIR"
    git pull
else
    step "Clonando repositório em $APP_DIR..."
    sudo git clone "$REPO_URL" "$APP_DIR"
    sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$APP_DIR"
    cd "$APP_DIR"
fi

# --------------------------------------------------------------------------- #
# 3. Ambiente virtual
# --------------------------------------------------------------------------- #
step "Criando ambiente virtual Python..."
python3 -m venv "$APP_DIR/venv"
source "$APP_DIR/venv/bin/activate"

# --------------------------------------------------------------------------- #
# 4. Instalar dependências Python
# --------------------------------------------------------------------------- #
step "Instalando dependências do requirements.txt..."
pip install --upgrade pip -q
pip install -r "$APP_DIR/requirements.txt" -q

# --------------------------------------------------------------------------- #
# 5. Criar .env a partir do exemplo (se não existir)
# --------------------------------------------------------------------------- #
if [ ! -f "$APP_DIR/.env" ]; then
    step "Criando arquivo .env..."
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    warn "ATENÇÃO: Edite o arquivo $APP_DIR/.env com suas credenciais antes de iniciar o bot!"
    warn "  nano $APP_DIR/.env"
else
    step ".env já existe — pulando criação."
fi

# --------------------------------------------------------------------------- #
# 6. Criar pasta de dados (SQLite)
# --------------------------------------------------------------------------- #
mkdir -p "$APP_DIR/data"

# --------------------------------------------------------------------------- #
# 7. Criar o serviço systemd
# --------------------------------------------------------------------------- #
step "Criando serviço systemd: $SERVICE_NAME..."

PYTHON_BIN="$APP_DIR/venv/bin/python"

sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Oráculo de Mesa — Agente IA Pessoal (Telegram Bot)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${PYTHON_BIN} main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# --------------------------------------------------------------------------- #
# 8. Ativar o serviço (mas NÃO iniciar ainda — falta o .env e o token.json)
# --------------------------------------------------------------------------- #
step "Registrando o serviço no systemd..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

# --------------------------------------------------------------------------- #
# RESUMO FINAL
# --------------------------------------------------------------------------- #
echo ""
echo "============================================================"
echo -e "${GREEN}✅ Instalação concluída!${NC}"
echo "============================================================"
echo ""
echo "Próximos passos OBRIGATÓRIOS antes de iniciar o bot:"
echo ""
echo "  1. Preencha as credenciais:"
echo "     nano $APP_DIR/.env"
echo ""
echo "  2. Transfira o token OAuth2 do Google Drive"
echo "     (gere localmente na sua máquina e copie com scp):"
echo "     scp client_secret.json usuario@servidor:$APP_DIR/"
echo "     scp token.json         usuario@servidor:$APP_DIR/"
echo ""
echo "  3. Inicie o bot:"
echo "     sudo systemctl start $SERVICE_NAME"
echo ""
echo "  4. Verifique os logs:"
echo "     sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "  Após configurado, o bot sobe automaticamente com o servidor"
echo "  e se reinicia em caso de falha (Restart=always)."
echo ""
echo "  Para atualizar o bot no futuro, use o próprio Telegram:"
echo "     /update"
echo "============================================================"
