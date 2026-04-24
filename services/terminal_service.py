import subprocess
import os
import platform
from config import logger

class TerminalService:
    """
    Serviço para execução de comandos no terminal do servidor.
    Permite ao agente interagir com o sistema operacional.
    """

    def __init__(self):
        self.is_linux = platform.system().lower() == "linux"

    def execute(self, command: str) -> str:
        """
        Executa um comando shell e retorna a saída (stdout + stderr).
        """
        logger.info(f"Executando comando no terminal: {command}")
        try:
            # Limitação básica de segurança: não permitir comandos interativos ou bloqueantes sem timeout
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                # Define o diretório de trabalho como a raiz do projeto se possível
                cwd=os.getcwd()
            )
            
            output = []
            if result.stdout:
                output.append(result.stdout)
            if result.stderr:
                output.append(f"ERRO: {result.stderr}")
            
            final_output = "\n".join(output).strip()
            if not final_output:
                return "Comando executado com sucesso (sem saída)."
            
            # Truncar saída se for muito longa para o Telegram/Gemini
            if len(final_output) > 4000:
                final_output = final_output[:4000] + "\n... (saída truncada)"
                
            return final_output

        except subprocess.TimeoutExpired:
            return "ERRO: O comando excedeu o tempo limite de 30 segundos."
        except Exception as e:
            return f"ERRO ao executar comando: {str(e)}"

terminal_service = TerminalService()
