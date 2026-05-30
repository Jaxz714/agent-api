"""CLI entry-point for agent-api."""

from __future__ import annotations

import json
import secrets
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from agentapi import __version__

console = Console()


@click.group()
@click.version_option(__version__, prog_name="agentapi")
def cli() -> None:
    """Agent API — turn any AI agent into an API service."""


@cli.command()
@click.option("--path", default="agent.yaml", help="Path for the generated config file.")
def init(path: str) -> None:
    """Create a sample agent.yaml configuration file."""
    from agentapi.config import write_default_config

    p = write_default_config(path)
    console.print(f"[green]Created config:[/green] {p}")


@cli.command()
@click.option("--config", "config_path", default=None, help="Path to agent.yaml config file.")
@click.option("--port", default=None, type=int, help="Override the port from config.")
@click.option("--host", default=None, help="Override the bind host from config.")
def serve(config_path: str | None, port: int | None, host: str | None) -> None:
    """Start the API server."""
    import uvicorn

    from agentapi.config import load_config
    from agentapi.server import create_app

    cfg = load_config(config_path)
    if port is not None:
        cfg.port = port
    if host is not None:
        cfg.host = host

    if not cfg.agents:
        console.print("[yellow]Warning:[/yellow] No agents configured. The server will start but no agent endpoints will be available.")

    console.print(f"[bold cyan]{cfg.name}[/bold cyan]")
    console.print(f"  Docs:  http://localhost:{cfg.port}/docs")
    console.print(f"  UI:    http://localhost:{cfg.port}/")
    console.print(f"  Health: http://localhost:{cfg.port}/health")
    for a in cfg.agents:
        console.print(f"  [green]{a.method}[/green] {a.path}  ({a.type})")
    console.print()

    app = create_app(config=cfg)
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")


@cli.command()
@click.option("--config", "config_path", default=None, help="Path to config file.")
@click.option("--limit", default=30, type=int, help="Number of log entries to show.")
def logs(config_path: str | None, limit: int) -> None:
    """View recent request logs from the SQLite database."""
    from agentapi.config import load_config
    from agentapi.logger import RequestLogger

    cfg = load_config(config_path)
    logger = RequestLogger(cfg.database)
    entries = logger.get_recent(limit)

    if not entries:
        console.print("[dim]No log entries yet.[/dim]")
        return

    table = Table(title="Recent Requests", show_lines=False)
    table.add_column("ID", style="dim", width=6)
    table.add_column("Timestamp", style="cyan", width=26)
    table.add_column("Method", width=6)
    table.add_column("Path", style="green")
    table.add_column("Status", width=8)
    table.add_column("Duration", width=10)
    table.add_column("Client", width=15)
    table.add_column("Key Prefix", width=14)

    for e in entries:
        status_style = "green" if e.status_code < 400 else "red"
        table.add_row(
            str(e.id),
            e.timestamp[:26],
            e.method,
            e.path,
            f"[{status_style}]{e.status_code}[/{status_style}]",
            f"{e.duration_ms:.0f}ms",
            e.client_ip,
            e.api_key_prefix,
        )

    console.print(table)


# ---- keys subgroup ----
@cli.group()
def keys() -> None:
    """Manage API keys."""


@keys.command("generate")
@click.option("--length", default=32, type=int, help="Key length in bytes (before sk- prefix).")
def keys_generate(length: int) -> None:
    """Generate a new random API key."""
    token = secrets.token_urlsafe(length)
    key = f"sk-{token}"
    console.print(f"[bold green]{key}[/bold green]")
    console.print()
    console.print("[dim]Add this key to your agent.yaml under auth.api_keys to use it.[/dim]")


# ---- test subgroup ----
@cli.command()
@click.argument("path")
@click.argument("input_text", default="hello")
@click.option("--config", "config_path", default=None, help="Path to config file.")
@click.option("--key", default=None, help="API key to use for the request.")
def test(path: str, input_text: str, config_path: str | None, key: str | None) -> None:
    """Test an agent endpoint by sending a request.

    Example: agentapi test /chat "hello"
    """
    import httpx

    from agentapi.config import load_config

    cfg = load_config(config_path)
    base_url = f"http://localhost:{cfg.port}"
    url = f"{base_url}{path}"

    headers = {"Content-Type": "application/json"}
    if key:
        headers[cfg.auth.header_name] = key

    payload = {"input": input_text}

    console.print(f"[cyan]POST[/cyan] {url}")
    console.print(f"[dim]Payload:[/dim] {json.dumps(payload)}")
    console.print()

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, json=payload, headers=headers)
            console.print(f"[bold]Status:[/bold] {resp.status_code}")
            try:
                data = resp.json()
                console.print_json(json.dumps(data, indent=2))
            except Exception:
                console.print(resp.text)
    except httpx.ConnectError:
        console.print(f"[red]Could not connect to {base_url}. Is the server running?[/red]")
        console.print("Start it with: [bold]agentapi serve[/bold]")
        sys.exit(1)
