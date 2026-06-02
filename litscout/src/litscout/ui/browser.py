from __future__ import annotations

import polars as pl
from rich import box
from rich.console import Console
from rich.table import Table

console = Console()

def browse_database_articles(articles_data: list[dict]):
    """Navegador interativo de artigos usando Polars para filtragem."""
    if not articles_data:
        console.print("[yellow]Nenhum artigo encontrado no banco.[/yellow]")
        return

    df = pl.DataFrame(articles_data)
    
    while True:
        # Prepara a tabela Rich
        table = Table(
            title="📚 Navegador de Conhecimento (Base Local)",
            box=box.ROUNDED,
            header_style="bold magenta",
            expand=True
        )
        table.add_column("ID", style="dim", width=4)
        table.add_column("Composto", style="bold cyan", width=15)
        table.add_column("Título", style="white", width=40)
        table.add_column("Autores", style="green", width=20)
        table.add_column("Ano", style="magenta", justify="center")
        table.add_column("Citações", style="yellow", justify="right")

        # Mostra os top 15 da visualização atual
        for row in df.head(15).to_dicts():
            title_disp = row["title"][:37] + "..." if len(row["title"]) > 40 else row["title"]
            
            authors = row["authors"]
            author_disp = authors[:17] + "..." if len(authors) > 20 else authors
            
            table.add_row(
                str(row["id"]),
                row["compound"],
                title_disp,
                author_disp,
                str(row["year"] or "-"),
                str(row["citation_count"])
            )

        console.clear()
        console.print(table)
        console.print(f"\n[dim]Exibindo {min(15, df.height)} de {df.height} artigos.[/dim]")
        console.print("\n[bold cyan]Opções de Filtro:[/bold cyan]")
        console.print("1. Filtrar por [bold white]Composto[/bold white]")
        console.print("2. Filtrar por [bold white]Título[/bold white]")
        console.print("3. Filtrar por [bold white]Autor[/bold white]")
        console.print("4. Filtrar por [bold white]Ano[/bold white]")
        console.print("5. Limpar Filtros")
        console.print("0. Voltar ao Menu Principal")

        from rich.prompt import Prompt
        sel_msg = "\n[bold green]? Selecione uma opção[/bold green]"
        choice = Prompt.ask(sel_msg, choices=["0", "1", "2", "3", "4", "5"], default="0")

        if choice == "0":
            break
        elif choice == "1":
            term = Prompt.ask("[bold yellow]Digite o nome do composto[/bold yellow]")
            df = df.filter(pl.col("compound").str.contains("(?i)" + term))
        elif choice == "2":
            term = Prompt.ask("[bold yellow]Digite o termo do título[/bold yellow]")
            df = df.filter(pl.col("title").str.contains("(?i)" + term))
        elif choice == "3":
            term = Prompt.ask("[bold yellow]Digite o nome do autor[/bold yellow]")
            df = df.filter(pl.col("authors").str.contains("(?i)" + term))
        elif choice == "4":
            term = Prompt.ask("[bold yellow]Digite o ano[/bold yellow]")
            if term.isdigit():
                df = df.filter(pl.col("year") == int(term))
        elif choice == "5":
            df = pl.DataFrame(articles_data)
