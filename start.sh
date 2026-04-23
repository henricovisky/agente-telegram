#!/usr/bin/env bash
# =============================================================================
# start.sh — Inicia o Henricovisky Bot
# Verifica se o ambiente está pronto; instala o que faltar antes de subir.
# Uso: bash start.sh
# =============================================================================

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$APP_DIR/venv"
PYTHON="$VENV/bin/python"
PIP="$VENV/bin/pip"
REQUIREMENTS="$APP_DIR/requirements.txt"
ENV_FILE="$APP_DIR/.env"
TOKEN_FILE="$APP_DIR/token.json"
SECRET_FILE="$APP_DIR/client_secret.json"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}  ✔ $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠  $1${NC}"; }
fail() { echo -e "${RED}  ✘ $1${NC}"; }
sep()  { echo -e "\n─────────────────────────────────────────"; }

echo ""
echo "🤖  Henricovisky — Verificação de ambiente"
sep

ERRORS=0

# ------------------------------------------------------------------ #
# 1. Python 3
# ------------------------------------------------------------------ #
if command -v python3 &>/dev/null; then
    ok "Python 3 encontrado: $(python3 --version)"
else
    fail "Python 3 não encontrado. Instale com: sudo apt-get install python3"
    ERRORS=$((ERRORS + 1))
fi

# ------------------------------------------------------------------ #
# 2. Ambiente virtual
# ------------------------------------------------------------------ #
if [ -d "$VENV" ]; then
    ok "venv encontrado em $VENV"
else
    warn "venv não existe — criando..."
    python3 -m venv "$VENV"
    ok "venv criado."
fi

# ------------------------------------------------------------------ #
# 3. Pacotes Python (requirements.txt)
# ------------------------------------------------------------------ #
# Verifica se o pacote-chave já está instalado como proxy rápido
if "$PYTHON" -c "import telegram" &>/dev/null; then
    ok "Dependências Python já instaladas."
else
    warn "Dependências não encontradas — instalando requirements.txt..."
    "$PIP" install --upgrade pip -q
    "$PIP" install -r "$REQUIREMENTS" -q
    ok "Dependências instaladas."
fi

# ------------------------------------------------------------------ #
# 4. Arquivo .env
# ------------------------------------------------------------------ #
if [ -f "$ENV_FILE" ]; then
    # Verifica se ainda tem o valor de placeholder
    if grep -q "your_telegram_bot_token_here" "$ENV_FILE"; then
        fail ".env existe mas ainda contém valores de exemplo."
        warn "Edite o arquivo: nano $ENV_FILE"
        ERRORS=$((ERRORS + 1))
    else
        ok ".env configurado."
    fi
else
    fail ".env não encontrado."
    if [ -f "$APP_DIR/.env.example" ]; then
        cp "$APP_DIR/.env.example" "$ENV_FILE"
        warn ".env criado a partir do .env.example — preencha suas credenciais:"
        warn "  nano $ENV_FILE"
    fi
    ERRORS=$((ERRORS + 1))
fi

# ------------------------------------------------------------------ #
# 5. Credenciais OAuth2 do Google Drive
# ------------------------------------------------------------------ #
if [ -f "$TOKEN_FILE" ]; then
    ok "token.json encontrado."
else
    warn "token.json não encontrado. O módulo Drive não vai funcionar."
    warn "Gere localmente e transfira: scp token.json usuario@servidor:$APP_DIR/"
fi

if [ -f "$SECRET_FILE" ]; then
    ok "client_secret.json encontrado."
else
    warn "client_secret.json não encontrado."
fi

# ------------------------------------------------------------------ #
# 6. Pasta de dados
# ------------------------------------------------------------------ #
mkdir -p "$APP_DIR/data"
ok "Pasta data/ pronta."

sep

# ------------------------------------------------------------------ #
# 7. Resultado
# ------------------------------------------------------------------ #
if [ "$ERRORS" -gt 0 ]; then
    echo ""
    fail "Encontrado(s) $ERRORS problema(s) crítico(s). Corrija antes de iniciar."
    echo ""
    exit 1
fi

echo ""
echo -e "${GREEN}✅  Ambiente OK — iniciando o bot...${NC}"
echo ""

# Carrega variáveis do .env no ambiente atual
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

exec "$PYTHON" "$APP_DIR/main.py"
