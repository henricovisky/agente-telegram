import asyncio
from fpdf import FPDF

from config import logger


class PdfService:
    """
    Encapsula a geração local de ficheiros PDF a partir de texto Markdown.
    Usa a biblioteca fpdf2 — sem APIs externas, sem custo recorrente.
    """

    # Fonte padrão (compatível com a maioria dos caracteres latinos)
    FONTE = 'helvetica'
    TAMANHO_FONTE = 12
    ALTURA_LINHA = 10  # Altura de cada linha em mm

    def __init__(self):
        """Inicializa o serviço de PDF."""
        pass

    async def criar_pdf(self, texto_markdown: str, caminho_saida: str) -> str:
        """
        Converte o texto (em formato Markdown) para um ficheiro PDF no disco local.

        Nota: A conversão de caracteres usa 'latin-1' com substituição de caracteres
        não suportados para evitar erros com carateres especiais do Português.

        Retorna o caminho do ficheiro PDF gerado.
        """
        logger.info(f"A gerar o PDF em '{caminho_saida}'...")
        loop = asyncio.get_running_loop()

        def _criar():
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()

            # Define a largura útil explicitamente para evitar erros de cálculo automático
            largura_util = pdf.w - pdf.l_margin - pdf.r_margin

            # Usando fonte Helvetica padrão e codificação latin-1 para compatibilidade
            pdf.set_font(self.FONTE, size=self.TAMANHO_FONTE)

            for linha in texto_markdown.split('\n'):
                # Força a codificação para latin-1, substituindo caracteres não suportados
                linha_segura = linha.encode('latin-1', 'replace').decode('latin-1')
                
                # Se a linha estiver vazia ou for apenas espaços, usa ln() para evitar erro no multi_cell
                if not linha_segura.strip():
                    pdf.ln(self.ALTURA_LINHA / 2)
                    continue
                
                # Garante que o cursor está na margem esquerda antes de cada parágrafo
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(largura_util, self.ALTURA_LINHA, txt=linha_segura)

            pdf.output(caminho_saida)
            logger.info("PDF gerado com sucesso.")

        await loop.run_in_executor(None, _criar)
        return caminho_saida
