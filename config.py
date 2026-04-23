import os
import logging
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do ficheiro .env
load_dotenv()

# --- Credenciais e Tokens ---
TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN', '')
GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', '')
DRIVE_CREDENTIALS_PATH: str = os.getenv('DRIVE_CREDENTIALS_PATH', 'client_secret.json')
DRIVE_FOLDER_ID: str = os.getenv('DRIVE_FOLDER_ID', '')

# --- Controle de Acesso ---
_raw_ids = os.getenv('ALLOWED_CHAT_IDS', '')
ALLOWED_CHAT_IDS: list[int] = [int(x) for x in _raw_ids.split(',') if x.strip()]


# --- Configuração de Logging ---
def configurar_logging() -> logging.Logger:
    """Configura e retorna o logger padrão da aplicação."""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    return logging.getLogger('oraculo_de_mesa')

# Logger global disponível para ser importado por outros módulos
logger = configurar_logging()
