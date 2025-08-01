"""Main CLI entry point for compute-forecast."""

import typer
from typing import Optional
from .. import __version__
from .commands.collect import main as collect_command
from .commands.consolidate_sessions import list_sessions, clean_sessions
from .commands.consolidate_parallel import main as consolidate_parallel_command
from .commands.quality import main as quality_command
from .commands.download import main as download_command


app = typer.Typer(
    name="compute-forecast",
    help="Compute Forecast - ML Research Computational Requirements Analysis. "
    "A tool for collecting and analyzing computational requirements from ML research papers "
    "to project future infrastructure needs.",
    add_completion=False,
)

# Register the collect command
app.command(name="collect")(collect_command)
app.command(name="consolidate")(consolidate_parallel_command)  # Use parallel version
app.command(name="download")(download_command)

# Create a subcommand group for consolidation sessions
consolidate_sessions_app = typer.Typer(help="Manage consolidation sessions")
consolidate_sessions_app.command(name="list")(list_sessions)
consolidate_sessions_app.command(name="clean")(clean_sessions)
app.add_typer(consolidate_sessions_app, name="consolidate-sessions")

# Register the quality command
app.command(name="quality")(quality_command)


def version_callback(value: bool):
    """Show version and exit."""
    if value:
        typer.echo(f"compute-forecast {__version__}")
        raise typer.Exit()


@app.callback()
def callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        help="Show version and exit.",
        is_eager=True,
    ),
):
    """
    Compute Forecast - ML Research Computational Requirements Analysis

    A comprehensive tool for collecting and analyzing computational requirements
    from ML research papers to project future infrastructure needs.
    """
    pass


def main():
    """Main entry point."""
    app()
