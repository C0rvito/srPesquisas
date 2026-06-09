from __future__ import annotations

import logging
import time
from pathlib import Path

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

from sr_pesquisas.config import settings
from sr_pesquisas.ui.tracer import trace_step

logger = logging.getLogger(__name__)

_ANALYSIS_PROMPT = """\
Você é um analista científico sênior. Você está realizando uma ANÁLISE PROFUNDA no seguinte artigo.
Composto de Interesse: "{query}"

Título do Artigo: {title}
DOI: {doi}
Abstract: {abstract}

Sua tarefa é fornecer um resumo técnico detalhado com "Principais Conclusões" (Key Takeaways).
Foque em:
1. Metodologia utilizada para ensaios de cito-toxicidade.
2. Concentrações específicas e resultados (IC50, LD50, etc.).
3. Se aplicável, descobertas detalhadas sobre Leishmania.
4. Conclusão final sobre o potencial do composto.

Responda em PORTUGUÊS (Brasil).
Formate sua resposta em Markdown, usando cabeçalhos, listas de tópicos e negrito para ênfase.
"""

class ArticleAnalyzer:
    """Gerencia a análise profunda de artigos específicos."""

    def __init__(self):
        self.llm = ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_summary_model,
            temperature=0.1
        )

    @trace_step("Análise Profunda via LLM")
    def analyze(self, query: str, title: str, doi: str | None, abstract: str | None) -> str:
        """Executa a análise profunda usando a LLM."""
        prompt = _ANALYSIS_PROMPT.format(
            query=query,
            title=title,
            doi=doi or "N/A",
            abstract=abstract or "Abstract não disponível para análise profunda."
        )

        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()

    def save_to_bib(self, query: str, analysis_md: str) -> str:
        """Salva a análise em um arquivo markdown no diretório bib/."""
        bib_dir = Path("bib")
        bib_dir.mkdir(exist_ok=True)

        # Sanitiza nome do arquivo
        filename = "".join(c for c in query if c.isalnum() or c in (" ", "_")).strip()
        file_path = bib_dir / f"{filename}.md"

        # Anexa ou cria novo
        mode = "a" if file_path.exists() else "w"
        if mode == "a":
            header = f"\n\n# Análise Profunda: {query}\n"
        else:
            header = f"# Índice de Análise Profunda: {query}\n"

        with open(file_path, mode, encoding="utf-8") as f:
            f.write(header)
            f.write(f"\n*Gerado em: {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            f.write(analysis_md)
            f.write("\n\n---\n")

        return str(file_path)

    def save_interaction(self, question: str, answer: str) -> str:
        """Salva uma pergunta e resposta na pasta bib/consultas.md."""
        bib_dir = Path("bib")
        bib_dir.mkdir(exist_ok=True)
        file_path = bib_dir / "consultas.md"
        
        mode = "a" if file_path.exists() else "w"
        with open(file_path, mode, encoding="utf-8") as f:
            if mode == "w":
                f.write("# Histórico de Consultas à Base de Conhecimento\n\n")
            f.write(f"## [{time.strftime('%Y-%m-%d %H:%M:%S')}] Pergunta\n")
            f.write(f"> {question}\n\n")
            f.write("### Resposta\n")
            f.write(f"{answer}\n\n---\n")
            
        return str(file_path)

