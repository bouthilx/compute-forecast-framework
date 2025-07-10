"""Main CLI entry point for compute-forecast."""

import typer
from typing import Optional
from .. import __version__
from .commands.collect import main as collect_command

app = typer.Typer(
    name="compute-forecast",
    help="Compute Forecast - ML Research Computational Requirements Analysis. "
    "A tool for collecting and analyzing computational requirements from ML research papers "
    "to project future infrastructure needs.",
    add_completion=False,
)

# Register the collect command
app.command(name="collect")(collect_command)


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
