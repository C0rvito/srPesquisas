from __future__ import annotations

from contextlib import contextmanager

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from litscout.utils.schemas import ArticleData

console = Console()

def display_welcome():
    """Display a welcome banner."""
    console.print(
        Panel(
            "[bold blue]🔬 LitScout[/bold blue] - AI-Powered Academic Scout",
            box=box.DOUBLE,
            border_style="blue"
        )
    )

def display_articles(articles: list[ArticleData], title: str = "Search Results"):
    """Display a list of articles in a formatted table."""
    table = Table(title=title, box=box.ROUNDED, show_lines=True)
    table.add_column("Rank", style="cyan", no_wrap=True)
    table.add_column("Title", style="white", width=60)
    table.add_column("Year", style="magenta")
    table.add_column("Citations", style="green")
    table.add_column("Venue", style="yellow")
    table.add_column("DOI", style="dim")

    for i, art in enumerate(articles, 1):
        table.add_row(
            str(i),
            art.title,
            str(art.year or "-"),
            str(art.citation_count),
            art.venue or "-",
            art.doi or "-"
        )

    console.print(table)

def display_sessions(sessions_data: list[dict]):
    """Display research sessions using Polars for formatting."""
    import polars as pl
    
    if not sessions_data:
        console.print("[yellow]No sessions found.[/yellow]")
        return

    df = pl.DataFrame(sessions_data)
    
    # Format date for better display
    df = df.with_columns(
        pl.col("created_at").dt.strftime("%Y-%m-%d %H:%M")
    )

    table = Table(title="Research Sessions", box=box.HORIZONTALS, header_style="bold magenta")
    table.add_column("ID", style="cyan")
    table.add_column("Query", style="white", width=40)
    table.add_column("Created At", style="green")
    table.add_column("Articles", style="yellow")

    for row in df.to_dicts():
        table.add_row(
            str(row["id"]),
            row["query"],
            row["created_at"],
            str(row["article_count"])
        )

    console.print(table)

def display_session_summary(session_id: int, query: str, count: int):
    """Display summary of a persisted session."""
    console.print(
        f"\n[bold green]✅ Success![/bold green] Session [bold]#{session_id}[/bold] saved."
    )
    console.print(f"Query: [italic]{query}[/italic]")
    console.print(f"Articles persisted: [bold]{count}[/bold]\n")

@contextmanager
def progress_spinner(description: str):
    """A context manager for showing a progress spinner."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description=description, total=None)
        yield
