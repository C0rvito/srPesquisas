from __future__ import annotations

import logging
from typing import Annotated

import typer
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from rich.logging import RichHandler
from rich.prompt import Prompt

from litscout.agents.analyzer import ArticleAnalyzer
from litscout.agents.pipeline import run_pipeline
from litscout.config import settings
from litscout.database.engine import db_session, init_db
from litscout.database.repository import (
    ArticleRepository,
    InteractionRepository,
    SessionRepository,
)
from litscout.ui.browser import browse_database_articles
from litscout.ui.display import (
    console,
    display_articles,
    display_session_summary,
    display_sessions,
    display_welcome,
)
from litscout.ui.tracer import tracer

# Configuração de logging em Português
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=console, show_time=False)]
)

app = typer.Typer(
    help="🔬 LitScout: Buscador acadêmico inteligente focado em cito-toxicidade.",
    add_completion=False,
)

db_app = typer.Typer(help="Gerenciar o banco de dados.")
app.add_typer(db_app, name="db")


@db_app.command("init")
def db_init():
    """Inicializa o banco de dados e cria as tabelas."""
    console.print("[bold blue]Inicializando banco de dados...[/bold blue]")
    init_db()
    console.print("[bold green]Banco de dados inicializado com sucesso![/bold green]")


@app.command("search")
def search(
    query: Annotated[
        str | None,
        typer.Argument(help="Termo de busca (ex: 'Carvacrol')")
    ] = None,
    top: Annotated[
        int,
        typer.Option("--top", "-t", help="Número de artigos para refinar")
    ] = 10,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Rodar sem salvar no banco")
    ] = False,
):
    """
    Busca literatura, ranqueia com IA e persiste os resultados.
    """
    display_welcome()

    if query is None or not isinstance(query, str):
        query = Prompt.ask("[bold green]? Digite o composto para pesquisar[/bold green]")

    tracer.reset_tree(f"Pesquisando: {query}")
    tracer.start_live()

    try:
        final_state = run_pipeline(query)
        tracer.stop_live()

        articles = (
            final_state.get("enriched_articles") or
            final_state.get("ranked_articles") or
            []
        )

        display_articles(articles[:top], title=f"Top {len(articles[:top])} Resultados para {query}")

        if not dry_run and final_state.get("db_session_id"):
            display_session_summary(
                final_state["db_session_id"],
                query,
                len(articles)
            )
        elif dry_run:
            console.print(
                "\n[yellow]⚠ Modo Dry-run: Nenhum dado foi salvo no banco.[/yellow]\n"
            )

    except Exception as exc:
        if tracer.live:
            tracer.stop_live()
        console.print(f"\n[bold red]❌ Erro Fatal:[/bold red] {exc}")


@app.command("sessions")
def list_sessions(limit: int = 10):
    """
    Lista o histórico de sessões de pesquisa.
    """
    with db_session() as session:
        repo = SessionRepository(session)
        sessions = repo.list_all(limit=limit)

        sessions_data = [
            {
                "id": s.id,
                "query": s.query,
                "created_at": s.created_at,
                "article_count": len(s.articles)
            }
            for s in sessions
        ]

        display_sessions(sessions_data)


@app.command("session")
def view_session(
    session_id: Annotated[int | None, typer.Argument(help="ID da sessão")] = None
):
    """
    Visualiza artigos de uma sessão e permite análise profunda.
    """
    if session_id is None:
        list_sessions()
        prompt_txt = "\n[bold green]? Digite o ID da Sessão para visualizar[/bold green]"
        session_id_str = Prompt.ask(prompt_txt)
        if not session_id_str.isdigit():
            return
        session_id = int(session_id_str)

    with db_session() as db:
        repo = SessionRepository(db)
        research_session = repo.get_with_articles(session_id)

        if not research_session:
            console.print(f"[red]Sessão #{session_id} não encontrada.[/red]")
            return

        articles_with_ranks = repo.get_session_articles(session_id)
        article_list = [a for a, _ in articles_with_ranks]

        console.print(f"\n[bold cyan]Sessão #{session_id}: {research_session.query}[/bold cyan]")
        display_articles(article_list, title=f"Artigos para {research_session.query}")

        sel_txt = "\n[bold green]? Selecione o Rank # para Análise (ou 0 para voltar)[/bold green]"
        choice = Prompt.ask(sel_txt, default="0")

        if choice.isdigit() and int(choice) > 0:
            idx = int(choice) - 1
            if 0 <= idx < len(articles_with_ranks):
                selected_article, _ = articles_with_ranks[idx]

                analyzer = ArticleAnalyzer()
                tracer.reset_tree(f"Análise Profunda: {selected_article.title[:50]}...")
                tracer.start_live()

                try:
                    analysis = analyzer.analyze(
                        query=research_session.query,
                        title=selected_article.title,
                        doi=selected_article.doi,
                        abstract=selected_article.abstract
                    )
                    tracer.stop_live()

                    path = analyzer.save_to_bib(research_session.query, analysis)
                    repo.update_analysis_path(session_id, path)

                    console.print("\n" + "="*40)
                    console.print("[bold green]Análise Concluída![/bold green]")
                    console.print(f"Salvo em: [bold]{path}[/bold]")
                    console.print("="*40 + "\n")
                    console.print(analysis)
                    console.print("\n" + "="*40)
                except Exception as exc:
                    if tracer.live:
                        tracer.stop_live()
                    console.print(f"[red]Falha na análise: {exc}[/red]")


@app.command("ask")
def ask_database(
    question: Annotated[
        str | None,
        typer.Argument(help="Pergunta para a base de conhecimento")
    ] = None
):
    """
    Faz uma pergunta à sua base de conhecimento local.
    """
    if not question:
        ask_txt = "\n[bold green]? O que você gostaria de saber sobre sua literatura?[/bold green]"
        question = Prompt.ask(ask_txt)

    with db_session() as db:
        art_repo = ArticleRepository(db)
        int_repo = InteractionRepository(db)

        # 1. Busca mais ampla (Keywords relaxadas)
        keywords = [w for w in question.replace("?", "").split() if len(w) > 3]
        
        relevant_articles = []
        seen_ids = set()
        
        # Se não houver palavras longas, pega as menores (exceto stop words comuns)
        if not keywords:
            keywords = [w for w in question.split() if len(w) > 2]

        for kw in keywords[:5]: # Aumentado para 5 keywords
            hits = art_repo.search_all_articles(kw, limit=15)
            for h in hits:
                if h.id not in seen_ids:
                    relevant_articles.append(h)
                    seen_ids.add(h.id)

        if not relevant_articles:
            # Tenta busca genérica se falhar nas keywords específicas
            relevant_articles = art_repo.search_all_articles("", limit=5)

        if not relevant_articles:
            console.print("[yellow]Nenhum dado relevante encontrado no banco.[/yellow]")
            return

        llm = ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_summary_model
        )

        context_list = []
        for a in relevant_articles[:8]:
            res = a.ai_summary or (a.abstract[:300] if a.abstract else "N/A")
            context_list.append(f"Título: {a.title}\nAutores: {a.authors}\nResumo IA: {res}")
        
        context = "\n\n".join(context_list)

        prompt = f"""\
Responda à pergunta baseando-se APENAS no contexto fornecido (vários artigos científicos).
O contexto contém títulos, autores e resumos.
Se não souber, diga que não há dados suficientes no banco local.
Responda em PORTUGUÊS (Brasil).

Pergunta: {question}

Contexto:
{context}

Resposta:
"""
        tracer.reset_tree("Consultando Base de Conhecimento")
        tracer.start_live()
        try:
            resp = llm.invoke([HumanMessage(content=prompt)])
            tracer.stop_live()
            answer = resp.content.strip()

            console.print("\n[bold cyan]── Resposta da Base de Conhecimento ──[/bold cyan]")
            console.print(answer)
            console.print(f"\n[dim]Baseado em {len(relevant_articles[:8])} artigos.[/dim]\n")
            
            analyzer = ArticleAnalyzer()
            file_path = analyzer.save_interaction(question, answer)
            int_repo.create(question=question, answer=answer, file_path=file_path)
            console.print(f"[dim]Consulta registrada em: {file_path}[/dim]")
            
        except Exception as exc:
            if tracer.live:
                tracer.stop_live()
            console.print(f"[red]Erro na consulta: {exc}[/red]")


@app.command("browse")
def browse_all():
    """
    Navega por todos os artigos do banco com filtros avançados.
    """
    with db_session() as db:
        repo = ArticleRepository(db)
        # O repositório já retorna uma lista de dicionários formatados
        articles_data = repo.get_all_articles()
        
        browse_database_articles(articles_data)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    LitScout: Ferramenta de pesquisa acadêmica com IA.
    """
    if ctx.invoked_subcommand is None:
        while True:
            display_welcome()
            console.print("\n[bold cyan]Menu Principal[/bold cyan]")
            console.print("1. [bold white]Nova Pesquisa (Busca)[/bold white]")
            console.print("2. [bold white]Ver Histórico (Sessões)[/bold white]")
            console.print("3. [bold white]Navegar Artigos (Filtros Avançados)[/bold white]")
            console.print("4. [bold white]Análise Profunda (Selecionar da Sessão)[/bold white]")
            console.print("5. [bold white]Perguntar ao Banco (Consulta Cruzada)[/bold white]")
            console.print("6. [bold white]Inicializar Banco[/bold white]")
            console.print("0. [bold white]Sair[/bold white]")

            choice = Prompt.ask(
                "\n[bold green]? Selecione uma opção[/bold green]",
                choices=["0", "1", "2", "3", "4", "5", "6"],
                default="1"
            )

            if choice == "1":
                search()
            elif choice == "2":
                list_sessions()
            elif choice == "3":
                browse_all()
            elif choice == "4":
                view_session()
            elif choice == "5":
                ask_database()
            elif choice == "6":
                db_init()
            else:
                console.print("[yellow]Até logo![/yellow]")
                break
            
            console.print("\n[dim]Pressione Enter para voltar ao menu...[/dim]")
            input()


if __name__ == "__main__":
    app()
