import re
import asyncio
from fpdf import FPDF

from config import logger


def _sanitizar(texto: str) -> str:
    """Converte texto para latin-1, substituindo caracteres não suportados."""
    return texto.encode('latin-1', 'replace').decode('latin-1')


class CronicaPDF(FPDF):
    """
    Subclasse de FPDF com cabeçalho e rodapé personalizados
    para a Crônica Épica de RPG.
    """

    def header(self):
        # Linha decorativa no topo de cada página
        self.set_draw_color(139, 90, 43)   # Marrom pergaminho
        self.set_line_width(0.8)
        self.line(self.l_margin, 14, self.w - self.r_margin, 14)

    def footer(self):
        self.set_y(-13)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 120, 80)
        self.cell(0, 10, _sanitizar(f'Crônica Épica  ·  Página {self.page_no()}'), align='C')
        # Linha decorativa no rodapé
        self.set_draw_color(139, 90, 43)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.h - 14, self.w - self.r_margin, self.h - 14)


class PdfService:
    """
    Encapsula a geração local de ficheiros PDF a partir de texto Markdown.
    Parseia Markdown (cabeçalhos, negrito, itálico, listas, réguas)
    e gera um documento visualmente agradável usando fpdf2.
    """

    # Margens (mm)
    MARGEM = 20

    def __init__(self):
        """Inicializa o serviço de PDF."""
        pass

    # ------------------------------------------------------------------
    # Renderizadores por tipo de linha Markdown
    # ------------------------------------------------------------------

    def _render_h1(self, pdf: CronicaPDF, texto: str, largura: float):
        """Título principal: fonte grande, negrito, cor dourada, centrado."""
        pdf.ln(6)
        pdf.set_font('Helvetica', 'B', 22)
        pdf.set_text_color(120, 80, 20)
        pdf.set_x(self.MARGEM)
        pdf.multi_cell(largura, 12, txt=_sanitizar(texto), align='C')
        # Sublinhado decorativo
        y = pdf.get_y()
        pdf.set_draw_color(139, 90, 43)
        pdf.set_line_width(0.6)
        pdf.line(self.MARGEM + 10, y + 1, pdf.w - self.MARGEM - 10, y + 1)
        pdf.ln(6)

    def _render_h2(self, pdf: CronicaPDF, texto: str, largura: float):
        """Subtítulo: fonte média, negrito, cor castanha."""
        pdf.ln(5)
        pdf.set_font('Helvetica', 'B', 15)
        pdf.set_text_color(100, 60, 20)
        pdf.set_x(self.MARGEM)
        pdf.multi_cell(largura, 9, txt=_sanitizar(texto))
        # Linha fina abaixo
        y = pdf.get_y()
        pdf.set_draw_color(180, 140, 80)
        pdf.set_line_width(0.3)
        pdf.line(self.MARGEM, y + 1, pdf.w - self.MARGEM, y + 1)
        pdf.ln(4)

    def _render_h3(self, pdf: CronicaPDF, texto: str, largura: float):
        """Sub-subtítulo: negrito, cor mais suave."""
        pdf.ln(3)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(80, 55, 25)
        pdf.set_x(self.MARGEM)
        pdf.multi_cell(largura, 8, txt=_sanitizar(texto))
        pdf.ln(2)

    def _render_hr(self, pdf: CronicaPDF):
        """Linha horizontal (---): linha ornamental centrada."""
        pdf.ln(3)
        pdf.set_draw_color(139, 90, 43)
        pdf.set_line_width(0.5)
        mid = pdf.w / 2
        pdf.line(mid - 30, pdf.get_y(), mid + 30, pdf.get_y())
        pdf.ln(5)

    def _render_bullet(self, pdf: CronicaPDF, texto: str, largura: float):
        """Item de lista com marcador personalizado."""
        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(40, 30, 20)
        # Recuo para o marcador
        recuo = 6
        pdf.set_x(self.MARGEM + recuo)
        # Marcador decorativo
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(5, 7, _sanitizar('\x95'), ln=False)   # bullet char
        pdf.set_font('Helvetica', '', 11)
        pdf.set_x(self.MARGEM + recuo + 5)
        pdf.multi_cell(largura - recuo - 5, 7, txt=_sanitizar(texto))

    def _render_paragrafo(self, pdf: CronicaPDF, texto: str, largura: float):
        """
        Parágrafo de texto normal. Parseia inline **negrito** e *itálico*
        imprimindo segmentos com a formatação correta.
        """
        pdf.set_text_color(30, 25, 15)
        pdf.set_x(self.MARGEM)

        # Divide o texto em segmentos pelo padrão **bold** ou *italic*
        partes = re.split(r'(\*\*[^*]+\*\*|\*[^*]+\*)', texto)
        altura = 7
        # Usamos write() para manter o fluxo inline
        for parte in partes:
            if parte.startswith('**') and parte.endswith('**'):
                pdf.set_font('Helvetica', 'B', 11)
                pdf.write(altura, _sanitizar(parte[2:-2]))
            elif parte.startswith('*') and parte.endswith('*'):
                pdf.set_font('Helvetica', 'I', 11)
                pdf.write(altura, _sanitizar(parte[1:-1]))
            else:
                pdf.set_font('Helvetica', '', 11)
                pdf.write(altura, _sanitizar(parte))
        pdf.ln(altura + 1)

    # ------------------------------------------------------------------
    # Método público principal
    # ------------------------------------------------------------------

    async def criar_pdf(self, texto_markdown: str, caminho_saida: str) -> str:
        """
        Converte o texto em formato Markdown para um ficheiro PDF formatado.
        Suporta: # H1, ## H2, ### H3, --- (hr), - lista, **negrito**, *itálico*.
        Retorna o caminho do ficheiro PDF gerado.
        """
        logger.info(f"A gerar o PDF em '{caminho_saida}'...")
        loop = asyncio.get_running_loop()

        def _criar():
            pdf = CronicaPDF()
            pdf.set_auto_page_break(auto=True, margin=20)
            pdf.set_margins(self.MARGEM, self.MARGEM, self.MARGEM)
            pdf.add_page()

            largura_util = pdf.w - 2 * self.MARGEM

            linhas = texto_markdown.split('\n')

            for linha in linhas:
                stripped = linha.strip()

                # Linha vazia → espaçamento
                if not stripped:
                    pdf.ln(3)
                    continue

                # H1
                if stripped.startswith('# '):
                    self._render_h1(pdf, stripped[2:].strip(), largura_util)

                # H2
                elif stripped.startswith('## '):
                    self._render_h2(pdf, stripped[3:].strip(), largura_util)

                # H3
                elif stripped.startswith('### '):
                    self._render_h3(pdf, stripped[4:].strip(), largura_util)

                # Régua horizontal (--- ou ***)
                elif re.match(r'^[-*]{3,}$', stripped):
                    self._render_hr(pdf)

                # Item de lista (- ou * ou + seguido de espaço)
                elif re.match(r'^[-*+] ', stripped):
                    self._render_bullet(pdf, stripped[2:].strip(), largura_util)

                # Parágrafo normal (com suporte a inline bold/italic)
                else:
                    self._render_paragrafo(pdf, stripped, largura_util)

            pdf.output(caminho_saida)
            logger.info("PDF gerado com sucesso.")

        await loop.run_in_executor(None, _criar)
        return caminho_saida
