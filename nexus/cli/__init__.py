"""NEXUS CLI — command-line interface powered by Typer + Rich."""

from __future__ import annotations

import asyncio
import logging
import sys

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

app = typer.Typer(
    name="nexus",
    help="NEXUS — Self-Evolving Multi-Agent Operating System",
    no_args_is_help=True,
)
console = Console()


def _setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


# ── nexus start ──────────────────────────────────────────────────────

@app.command()
def start(
    port: int = typer.Option(8000, help="API server port"),
    log_level: str = typer.Option("INFO", help="Log level"),
) -> None:
    """Boot the NEXUS kernel and start the API server."""
    _setup_logging(log_level)

    console.print(
        Panel(
            Text.from_markup(
                "[bold cyan]NEXUS[/] — Self-Evolving Multi-Agent OS\n"
                f"[dim]Starting on port {port}...[/]"
            ),
            border_style="cyan",
        )
    )

    import uvicorn
    from nexus.api.server import create_app

    uvicorn_app = create_app()
    uvicorn.run(uvicorn_app, host="0.0.0.0", port=port, log_level=log_level.lower())


# ── nexus run ────────────────────────────────────────────────────────

@app.command()
def run(
    task: str = typer.Argument(..., help="Task description"),
    model: str = typer.Option(None, help="LLM model to use"),
    log_level: str = typer.Option("INFO", help="Log level"),
) -> None:
    """Submit a task and wait for the result."""
    _setup_logging(log_level)

    console.print(f"\n[bold cyan]NEXUS[/] — Running task: [yellow]{task}[/]\n")

    async def _run() -> None:
        from nexus.kernel.kernel import Kernel

        kernel = Kernel()
        if model:
            kernel.config.default_model = model
        await kernel.boot()

        console.print("[dim]Kernel booted. Processing task...[/]\n")

        result_task = await kernel.run_task(task)

        if result_task.status.value == "completed":
            console.print(Panel(
                str(result_task.result),
                title="[green]✓ Result[/]",
                border_style="green",
            ))
        else:
            console.print(Panel(
                str(result_task.error),
                title="[red]✗ Failed[/]",
                border_style="red",
            ))

        await kernel.shutdown()

    asyncio.run(_run())


# ── nexus shell ──────────────────────────────────────────────────────

@app.command()
def shell(
    log_level: str = typer.Option("WARNING", help="Log level"),
) -> None:
    """Interactive NEXUS shell — submit tasks interactively."""
    _setup_logging(log_level)

    console.print(
        Panel(
            "[bold cyan]NEXUS Shell[/]\n"
            "[dim]Type tasks and press Enter. Type 'exit' to quit.[/]",
            border_style="cyan",
        )
    )

    async def _shell() -> None:
        from nexus.kernel.kernel import Kernel

        kernel = Kernel()
        await kernel.boot()
        console.print(f"[dim]Kernel booted. {len(kernel.tool_registry.list_tools())} tools available.[/]\n")

        while True:
            try:
                task_input = console.input("[bold cyan]nexus>[/] ")
            except (EOFError, KeyboardInterrupt):
                break

            task_input = task_input.strip()
            if not task_input:
                continue
            if task_input.lower() in ("exit", "quit", "q"):
                break

            # Handle built-in commands
            if task_input == "agents":
                agents = kernel.agent_registry.list_all()
                if not agents:
                    console.print("[dim]No active agents.[/]")
                else:
                    table = Table(title="Active Agents")
                    table.add_column("ID")
                    table.add_column("Type")
                    table.add_column("Status")
                    table.add_column("Capabilities")
                    for a in agents:
                        table.add_row(a.id, a.type, a.status.value, ", ".join(a.capabilities))
                    console.print(table)
                continue

            if task_input == "tools":
                tools = kernel.tool_registry.list_tools()
                table = Table(title="Registered Tools")
                table.add_column("Name")
                table.add_column("Description")
                table.add_column("Built-in")
                table.add_column("Uses")
                for t in tools:
                    table.add_row(t.name, t.description[:60], str(t.is_builtin), str(t.usage_count))
                console.print(table)
                continue

            # Run as task
            try:
                result_task = await kernel.run_task(task_input)
                if result_task.status.value == "completed":
                    console.print(f"\n[green]{result_task.result}[/]\n")
                else:
                    console.print(f"\n[red]Failed: {result_task.error}[/]\n")
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/]\n")

        await kernel.shutdown()
        console.print("[dim]NEXUS shut down.[/]")

    asyncio.run(_shell())


# ── nexus agents ─────────────────────────────────────────────────────

agents_app = typer.Typer(help="Manage agents")
app.add_typer(agents_app, name="agents")


@agents_app.command("list")
def agents_list() -> None:
    """List all active agents (requires running server)."""
    import httpx
    try:
        resp = httpx.get("http://localhost:8000/api/agents")
        resp.raise_for_status()
        agents = resp.json()
        if not agents:
            console.print("[dim]No active agents.[/]")
            return
        table = Table(title="Active Agents")
        table.add_column("ID")
        table.add_column("Type")
        table.add_column("Status")
        table.add_column("Tokens Used")
        for a in agents:
            table.add_row(a["id"], a["type"], a["status"], str(a.get("tokens_used", 0)))
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error connecting to NEXUS API: {e}[/]")


# ── nexus tools ──────────────────────────────────────────────────────

tools_app = typer.Typer(help="Manage MCP tools")
app.add_typer(tools_app, name="tools")


@tools_app.command("list")
def tools_list() -> None:
    """List all registered MCP tools (requires running server)."""
    import httpx
    try:
        resp = httpx.get("http://localhost:8000/api/tools")
        resp.raise_for_status()
        tools = resp.json()
        table = Table(title="MCP Tools")
        table.add_column("Name")
        table.add_column("Description")
        table.add_column("Built-in")
        table.add_column("Uses")
        for t in tools:
            table.add_row(t["name"], t["description"][:60], str(t["is_builtin"]), str(t["usage_count"]))
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error connecting to NEXUS API: {e}[/]")


if __name__ == "__main__":
    app()
