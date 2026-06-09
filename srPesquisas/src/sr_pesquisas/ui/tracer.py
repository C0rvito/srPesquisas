from __future__ import annotations

import time
from functools import wraps

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree


class ExecutionTracer:
    """Rastreia e renderiza o mapa de execução de forma limpa."""

    def __init__(self, title: str):
        self.console = Console()
        self.title = title
        self.root = Tree(f"[bold cyan]󱓞 {title}[/bold cyan]")
        self.stack = [self.root]
        self.status = None

    def start_live(self):
        """Inicia um spinner de status global em vez de um painel Live repetitivo."""
        if self.status is None:
            msg = "[bold yellow]Iniciando processamento...[/bold yellow]"
            self.status = self.console.status(msg)
            self.status.start()

    def stop_live(self, show_final: bool = True):
        """Finaliza o status e imprime a árvore final consolidada."""
        if self.status:
            self.status.stop()
            self.status = None

        if show_final:
            self.console.print("\n")
            self.console.print(self.get_renderable())
            self.console.print("\n")

    def get_renderable(self):
        """Retorna o painel formatado com a árvore de execução."""
        return Panel(
            self.root,
            title=f"[bold white]{self.title}[/bold white]",
            border_style="bright_blue",
            box=box.DOUBLE_EDGE,
            padding=(1, 2),
        )

    def push(self, name: str):
        """Adiciona um passo ao rastreamento e atualiza o spinner."""
        node = self.stack[-1].add(f"[bold yellow]󱎫 {name}...[/bold yellow]")
        self.stack.append(node)
        if self.status:
            self.status.update(f"[bold yellow]Executando: {name}...[/bold yellow]")
        return node

    def pop(self, node, name: str, success: bool, duration: float):
        """Finaliza um passo no rastreamento."""
        self.stack.pop()
        if success:
            node.label = f"[bold green]󰄬 {name}[/bold green] [dim]({duration:.3f}s)[/dim]"
        else:
            node.label = f"[bold red]󰅙 {name}[/bold red] [dim]({duration:.3f}s)[/dim]"

    def reset_tree(self, new_title: str):
        """Reseta a árvore para um novo bloco de análise."""
        self.title = new_title
        self.root = Tree(f"[bold cyan]󱓞 {new_title}[/bold cyan]")
        self.stack = [self.root]


# Instância global do tracer
tracer = ExecutionTracer("srPesquisas - Pipeline de Pesquisa")


def trace_step(name: str):
    """Decorador para rastrear o ciclo de vida e mostrar status em tempo real."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            node = tracer.push(name)
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                tracer.pop(node, name, success=True, duration=duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                tracer.pop(node, name, success=False, duration=duration)
                if tracer.status:
                    tracer.stop_live(show_final=False)
                tracer.console.print(f"\n[bold red]── ERRO EM: {name} ──[/bold red]")
                tracer.console.print(f"[red]{e}[/red]\n")
                raise e

        return wrapper

    return decorator
