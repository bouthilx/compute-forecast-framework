"""
Session management commands for consolidation.
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from datetime import datetime

from compute_forecast.pipeline.consolidation.checkpoint_manager import ConsolidationCheckpointManager

console = Console()


def list_sessions(
    checkpoint_dir: Path = typer.Option(Path(".cf_state/consolidate"), "--checkpoint-dir", help="Checkpoint directory"),
    all: bool = typer.Option(False, "--all", "-a", help="Show all sessions including completed"),
):
    """
    List consolidation sessions with their status.
    """
    sessions = ConsolidationCheckpointManager.find_resumable_sessions(checkpoint_dir)
    
    if not sessions:
        console.print("[yellow]No consolidation sessions found.[/yellow]")
        return
    
    # Filter if not showing all
    if not all:
        sessions = [s for s in sessions if s["status"] in ["interrupted", "failed"]]
        if not sessions:
            console.print("[yellow]No resumable sessions found. Use --all to see completed sessions.[/yellow]")
            return
    
    # Create table
    table = Table(title="Consolidation Sessions")
    table.add_column("Session ID", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Input File")
    table.add_column("Papers")
    table.add_column("Sources")
    table.add_column("Created", style="dim")
    table.add_column("Last Checkpoint", style="dim")
    
    for session in sessions:
        # Format status with color
        status = session["status"]
        if status == "completed":
            status = f"[green]{status}[/green]"
        elif status == "failed":
            status = f"[red]{status}[/red]"
        elif status == "interrupted":
            status = f"[yellow]{status}[/yellow]"
        else:
            status = f"[dim]{status}[/dim]"
        
        # Format timestamps
        created = datetime.fromisoformat(session["created_at"]).strftime("%Y-%m-%d %H:%M")
        last_checkpoint = datetime.fromisoformat(session["last_checkpoint"]).strftime("%Y-%m-%d %H:%M")
        
        # Add row
        table.add_row(
            session["session_id"],
            status,
            session["input_file"],
            str(session["total_papers"]),
            ", ".join(session["sources"]),
            created,
            last_checkpoint
        )
    
    console.print(table)
    
    # Show summary
    resumable = [s for s in sessions if s["status"] in ["interrupted", "failed"]]
    if resumable:
        console.print(f"\n[cyan]{len(resumable)} resumable session(s) available.[/cyan]")
        console.print("Use [bold]cf consolidate --resume --input <file>[/bold] to resume.")


def clean_sessions(
    checkpoint_dir: Path = typer.Option(Path(".cf_state/consolidate"), "--checkpoint-dir", help="Checkpoint directory"),
    completed: bool = typer.Option(False, "--completed", help="Clean only completed sessions"),
    all: bool = typer.Option(False, "--all", help="Clean all sessions (use with caution)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be cleaned"),
):
    """
    Clean up old consolidation sessions.
    """
    import shutil
    
    sessions = ConsolidationCheckpointManager.find_resumable_sessions(checkpoint_dir)
    
    if not sessions:
        console.print("[yellow]No sessions to clean.[/yellow]")
        return
    
    # Filter based on options
    if completed:
        to_clean = [s for s in sessions if s["status"] == "completed"]
    elif all:
        to_clean = sessions
    else:
        console.print("[red]Please specify --completed or --all[/red]")
        return
    
    if not to_clean:
        console.print("[yellow]No sessions match the criteria.[/yellow]")
        return
    
    # Show what will be cleaned
    console.print(f"[yellow]Will clean {len(to_clean)} session(s):[/yellow]")
    for session in to_clean:
        console.print(f"  • {session['session_id']} ({session['status']}) - {session['input_file']}")
    
    if dry_run:
        console.print("\n[dim]Dry run - no changes made.[/dim]")
        return
    
    if not typer.confirm("\nProceed with cleanup?"):
        return
    
    # Perform cleanup
    cleaned = 0
    for session in to_clean:
        session_dir = checkpoint_dir / session["session_id"]
        try:
            shutil.rmtree(session_dir)
            cleaned += 1
        except Exception as e:
            console.print(f"[red]Failed to clean {session['session_id']}: {e}[/red]")
    
    console.print(f"\n[green]Cleaned {cleaned} session(s).[/green]")