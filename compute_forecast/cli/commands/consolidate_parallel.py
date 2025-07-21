"""Parallel consolidation command."""

import typer
from pathlib import Path
import json
from datetime import datetime
from typing import Optional
import logging
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    ProgressColumn,
    Task,
)
from rich.text import Text
from rich.live import Live
from datetime import timedelta

from compute_forecast.pipeline.consolidation.parallel.consolidator import ParallelConsolidator
from compute_forecast.pipeline.consolidation.checkpoint_manager import ConsolidationCheckpointManager
from compute_forecast.pipeline.consolidation.models_extended import ConsolidationPhaseState
from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.utils.profiling import PerformanceProfiler, set_profiler
from compute_forecast.cli.utils.logging_handler import RichConsoleHandler
from compute_forecast.cli.commands.consolidate import load_papers, save_papers

console = Console()
logger = logging.getLogger(__name__)


class ParallelProgressColumn(ProgressColumn):
    """Custom progress column showing: <progress>%, (<n done>/<total>) DD HH:MM:SS (YYYY-MM-DD HH:MM:SS ETA) [citations:<n> abstracts:<n>]"""
    
    def __init__(self):
        super().__init__()
        # Store citation/abstract counts per task
        self.task_stats = {}
    
    def update_stats(self, task_id, citations: int, abstracts: int):
        """Update citation/abstract stats for a task."""
        self.task_stats[task_id] = {'citations': citations, 'abstracts': abstracts}
    
    def render(self, task: Task) -> Text:
        """Render the progress details."""
        if task.total is None:
            return Text("")
        
        # Calculate percentage
        percentage = (task.completed / task.total) * 100 if task.total > 0 else 0
        
        # Format elapsed time
        elapsed = task.elapsed
        if elapsed is None:
            elapsed_str = "00:00:00"
        else:
            days = int(elapsed // 86400)
            hours = int((elapsed % 86400) // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            
            if days > 0:
                elapsed_str = f"{days:02d} {hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                elapsed_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Calculate ETA
        if task.speed and task.remaining:
            eta_seconds = task.remaining / task.speed
            eta_time = datetime.now() + timedelta(seconds=eta_seconds)
            eta_str = eta_time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            eta_str = "Unknown"
        
        # Get citation/abstract stats
        stats = self.task_stats.get(task.id, {'citations': 0, 'abstracts': 0})
        
        # Format the complete string
        text = f"{percentage:5.1f}%, ({task.completed}/{task.total}) {elapsed_str} ({eta_str} ETA) [citations:{stats['citations']} abstracts:{stats['abstracts']}]"
        
        return Text(text, style="cyan")


def main(
    input: Path = typer.Option(..., "--input", "-i", help="Input JSON file from collect"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable progress bars"),
    ss_api_key: Optional[str] = typer.Option(None, "--ss-api-key", help="Semantic Scholar API key", envvar="SEMANTIC_SCHOLAR_API_KEY"),
    openalex_email: Optional[str] = typer.Option(None, "--openalex-email", help="OpenAlex email", envvar="OPENALEX_EMAIL"),
    profile: bool = typer.Option(False, "--profile", help="Enable performance profiling"),
    resume: bool = typer.Option(False, "--resume", help="Resume from previous checkpoint if available"),
    checkpoint_interval: float = typer.Option(5.0, "--checkpoint-interval", help="Minutes between checkpoints (0 to disable)"),
    phase1_batch_size: int = typer.Option(1, "--phase1-batch-size", help="Batch size for Phase 1 (OpenAlex ID harvesting)"),
    phase2_batch_size: int = typer.Option(500, "--phase2-batch-size", help="Batch size for Phase 2 (Semantic Scholar enrichment)"),
    phase3_batch_size: int = typer.Option(50, "--phase3-batch-size", help="Batch size for Phase 3 (OpenAlex enrichment)"),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True, help="Increase verbosity level (-v for INFO, -vv for DEBUG)"),
):
    """
    Parallel consolidation and enrichment of paper metadata.
    
    This command uses a parallel approach:
    - OpenAlex and Semantic Scholar process papers simultaneously
    - Results are merged with proper attribution
    - No ineffective ID harvesting phase
    
    Examples:
        cf consolidate-parallel --input papers.json --output enriched.json
        cf consolidate-parallel --input papers.json --resume  # Resume from checkpoint
        cf consolidate-parallel --input papers.json -v     # INFO level logging
        cf consolidate-parallel --input papers.json -vv    # DEBUG level logging
    """
    
    # Configure logging based on verbosity
    log_level = logging.WARNING
    if verbose >= 2:
        log_level = logging.DEBUG
    elif verbose >= 1:
        log_level = logging.INFO
        
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[]  # Clear default handlers
    )
    
    # Set default output
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = Path(f"data/consolidated_papers/papers_{timestamp}.json")
    
    # Initialize profiler if requested
    if profile:
        profiler = PerformanceProfiler("consolidation")
        set_profiler(profiler)
    
    # Initialize checkpoint manager
    session_id = None
    if resume:
        # Find existing session for this input file
        session_id = ConsolidationCheckpointManager.get_latest_resumable_session(str(input))
        if not session_id:
            console.print(f"[yellow]No resumable session found for {input}[/yellow]")
            resume = False
    
    checkpoint_manager = ConsolidationCheckpointManager(
        session_id=session_id,
        checkpoint_interval_minutes=checkpoint_interval
    )
    
    # Initialize phase state
    phase_state = ConsolidationPhaseState(phase="parallel_consolidation")
    
    # Check for resume
    checkpoint_data = None
    papers = None
    actual_stats = None
    
    if resume:
        checkpoint_result = checkpoint_manager.load_checkpoint()
        if checkpoint_result:
            checkpoint_data, papers = checkpoint_result
            console.print(f"[green]Resuming from checkpoint: {checkpoint_data.session_id}[/green]")
            console.print(f"  Papers loaded: {len(papers)}")
            
            # Restore phase state if available
            if hasattr(checkpoint_data, 'phase_state') and checkpoint_data.phase_state:
                phase_state = ConsolidationPhaseState.from_dict(checkpoint_data.phase_state)
                console.print(f"  Current phase: {phase_state.phase}")
                console.print(f"  OpenAlex processed: {len(phase_state.openalex_processed_hashes)}")
                console.print(f"  Semantic Scholar processed: {len(phase_state.semantic_scholar_processed_hashes)}")
            
            # Count actual enriched papers from the loaded file
            actual_stats = {
                'openalex': {
                    'papers_processed': checkpoint_data.sources.get('openalex', {}).get('papers_processed', 0),
                    'papers_enriched': 0,
                    'citations_found': 0,
                    'abstracts_found': 0
                },
                'semantic_scholar': {
                    'papers_processed': checkpoint_data.sources.get('semantic_scholar', {}).get('papers_processed', 0),
                    'papers_enriched': 0,
                    'citations_found': 0,
                    'abstracts_found': 0
                }
            }
            
            # Check if we have the enriched papers file
            enriched_file = checkpoint_manager.checkpoint_dir / "papers_enriched.json"
            if enriched_file.exists():
                try:
                    with open(enriched_file) as f:
                        data = json.load(f)
                    
                    papers_data = data.get("papers", [])
                    
                    # Count actual enriched papers and content
                    for paper in papers_data:
                        # Check OpenAlex
                        has_oa_data = False
                        has_oa_citation = False
                        has_oa_abstract = False
                        
                        if paper.get("openalex_id"):
                            has_oa_data = True
                            
                        if paper.get("citations"):
                            for citation in paper["citations"]:
                                if citation.get("source") == "openalex":
                                    has_oa_data = True
                                    has_oa_citation = True
                                    break
                                    
                        if paper.get("abstracts"):
                            for abstract in paper["abstracts"]:
                                if abstract.get("source") == "openalex":
                                    has_oa_data = True
                                    has_oa_abstract = True
                                    break
                        
                        if has_oa_data:
                            actual_stats['openalex']['papers_enriched'] += 1
                        if has_oa_citation:
                            actual_stats['openalex']['citations_found'] += 1
                        if has_oa_abstract:
                            actual_stats['openalex']['abstracts_found'] += 1
                        
                        # Check Semantic Scholar
                        has_ss_data = False
                        has_ss_citation = False
                        has_ss_abstract = False
                        
                        if paper.get("external_ids", {}).get("semantic_scholar"):
                            has_ss_data = True
                            
                        if paper.get("citations"):
                            for citation in paper["citations"]:
                                if citation.get("source") == "semanticscholar":
                                    has_ss_data = True
                                    has_ss_citation = True
                                    break
                                    
                        if paper.get("abstracts"):
                            for abstract in paper["abstracts"]:
                                if abstract.get("source") == "semanticscholar":
                                    has_ss_data = True
                                    has_ss_abstract = True
                                    break
                        
                        if has_ss_data:
                            actual_stats['semantic_scholar']['papers_enriched'] += 1
                        if has_ss_citation:
                            actual_stats['semantic_scholar']['citations_found'] += 1
                        if has_ss_abstract:
                            actual_stats['semantic_scholar']['abstracts_found'] += 1
                    
                    console.print(f"\n[cyan]Actual enrichment statistics from file:[/cyan]")
                    console.print(f"  OpenAlex: {actual_stats['openalex']['papers_enriched']} enriched, "
                                f"{actual_stats['openalex']['citations_found']} citations, "
                                f"{actual_stats['openalex']['abstracts_found']} abstracts")
                    console.print(f"  Semantic Scholar: {actual_stats['semantic_scholar']['papers_enriched']} enriched, "
                                f"{actual_stats['semantic_scholar']['citations_found']} citations, "
                                f"{actual_stats['semantic_scholar']['abstracts_found']} abstracts")
                    
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not read enriched papers file: {e}[/yellow]")
                    actual_stats = None
                    
        else:
            console.print("[yellow]No valid checkpoint found, starting from beginning[/yellow]")
    
    # Load papers if not resuming
    if papers is None:
        console.print(f"[cyan]Loading papers from {input}...[/cyan]")
        papers = load_papers(input)
        console.print(f"[green]Loaded {len(papers)} papers[/green]")
    
    if dry_run:
        console.print("\n[yellow]DRY RUN - Parallel consolidation:[/yellow]")
        console.print(f"  Papers: {len(papers)}")
        console.print(f"  Checkpoint interval: {checkpoint_interval} minutes")
        return
    
    # Create consolidator
    consolidator = ParallelConsolidator(
        openalex_email=openalex_email,
        ss_api_key=ss_api_key,
        openalex_batch_size=1,  # Always 1 for title search
        ss_batch_size=1,  # Always 1 for title search
        checkpoint_manager=checkpoint_manager,
        checkpoint_interval=checkpoint_interval * 60  # Convert to seconds
    )
    
    # Load checkpoint state if resuming
    existing_papers = []
    if resume and phase_state:
        existing_papers = consolidator.load_checkpoint(phase_state)
    
    # Create custom progress column
    progress_column = ParallelProgressColumn()
    
    # Create progress display with two bars
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        progress_column,
        console=console,
        disable=no_progress,
    )
    
    with Live(progress, console=console, refresh_per_second=4, vertical_overflow="visible", transient=True) as live:
        # Add custom logging handler
        rich_handler = RichConsoleHandler(console, live)
        rich_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(rich_handler)
        
        # Create progress bars
        openalex_task = progress.add_task(
            "[cyan]OpenAlex[/cyan]",
            total=len(papers)
        )
        
        ss_task = progress.add_task(
            "[green]Semantic Scholar[/green]",
            total=len(papers)
        )
        
        # If resuming, set initial progress
        if resume and (actual_stats or (checkpoint_data and hasattr(checkpoint_data, 'sources'))):
            # Use actual stats if available, otherwise use checkpoint stats
            stats_to_use = actual_stats if actual_stats else checkpoint_data.sources
            oa_stats = stats_to_use.get('openalex', {})
            ss_stats = stats_to_use.get('semantic_scholar', {})
            
            # Set initial progress
            oa_processed = oa_stats.get('papers_processed', 0)
            ss_processed = ss_stats.get('papers_processed', 0)
            
            if oa_processed > 0:
                progress.update(openalex_task, completed=oa_processed)
                progress_column.update_stats(
                    openalex_task, 
                    oa_stats.get('citations_found', 0),
                    oa_stats.get('abstracts_found', 0)
                )
                
            if ss_processed > 0:
                progress.update(ss_task, completed=ss_processed)
                progress_column.update_stats(
                    ss_task,
                    ss_stats.get('citations_found', 0),
                    ss_stats.get('abstracts_found', 0)
                )
                
            # Log the actual statistics being used
            console.print(f"\n[cyan]Starting with statistics:[/cyan]")
            console.print(f"  OpenAlex: {oa_processed} processed, {oa_stats.get('papers_enriched', 0)} enriched")
            console.print(f"  Semantic Scholar: {ss_processed} processed, {ss_stats.get('papers_enriched', 0)} enriched")
        
        # Define progress callback
        def update_progress(source: str, count: int, citations: int, abstracts: int):
            logger.debug(f"Progress update: {source} - count:{count}, citations:{citations}, abstracts:{abstracts}")
            if source == 'openalex':
                progress.advance(openalex_task, count)
                progress_column.update_stats(openalex_task, citations, abstracts)
            elif source == 'semantic_scholar':
                progress.advance(ss_task, count)
                progress_column.update_stats(ss_task, citations, abstracts)
        
        # Process papers
        console.print("\n[bold cyan]Starting Parallel Consolidation[/bold cyan]")
        start_time = datetime.now()
        
        # Pass checkpoint stats if resuming
        checkpoint_stats = None
        if resume and checkpoint_data and hasattr(checkpoint_data, 'sources'):
            # Use actual stats if we calculated them, otherwise use checkpoint stats
            if actual_stats:
                checkpoint_stats = actual_stats
            else:
                checkpoint_stats = checkpoint_data.sources
            
        enriched_papers = consolidator.process_papers(
            papers, 
            update_progress,
            input_file=str(input),
            checkpoint_papers=papers,
            checkpoint_stats=checkpoint_stats
        )
        
        # Merge with any existing papers from checkpoint
        if existing_papers:
            # Create a dict for fast lookup
            enriched_dict = {p.paper_id: p for p in enriched_papers}
            
            # Add any papers from checkpoint that aren't in the new results
            for existing_paper in existing_papers:
                if existing_paper.paper_id not in enriched_dict:
                    enriched_papers.append(existing_paper)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Ensure progress shows 100%
        progress.update(openalex_task, completed=len(papers))
        progress.update(ss_task, completed=len(papers))
    
    # Calculate enrichment statistics
    citation_count = sum(1 for p in enriched_papers if p.citations)
    abstract_count = sum(1 for p in enriched_papers if p.abstracts)
    doi_count = sum(1 for p in enriched_papers if p.doi)
    arxiv_count = sum(1 for p in enriched_papers if p.arxiv_id)
    
    # Collect statistics for save_papers
    stats = {
        "total_papers": len(enriched_papers),
        "duration_seconds": duration,
        "papers_per_second": len(papers)/duration,
        "papers_with_citations": citation_count,
        "papers_with_abstracts": abstract_count,
        "papers_with_dois": doi_count,
        "papers_with_arxiv": arxiv_count,
        "method": "parallel"
    }
    
    # Save results
    console.print(f"\n[cyan]Saving {len(enriched_papers)} enriched papers to {output}...[/cyan]")
    save_papers(enriched_papers, output, stats)
    
    # Report summary
    console.print(f"\n[green]Consolidation Complete:[/green]")
    console.print(f"  Total papers: {len(enriched_papers)}")
    console.print(f"  Duration: {duration:.1f}s")
    console.print(f"  Papers/second: {len(papers)/duration:.1f}")
    
    # Report enrichment statistics
    console.print(f"\n[green]Enrichment Statistics:[/green]")
    console.print(f"  Papers with citations: {citation_count} ({citation_count/len(enriched_papers)*100:.1f}%)")
    console.print(f"  Papers with abstracts: {abstract_count} ({abstract_count/len(enriched_papers)*100:.1f}%)")
    console.print(f"  Papers with DOIs: {doi_count} ({doi_count/len(enriched_papers)*100:.1f}%)")
    console.print(f"  Papers with ArXiv IDs: {arxiv_count} ({arxiv_count/len(enriched_papers)*100:.1f}%)")
    
    if profile and profiler:
        console.print("\n[yellow]Performance Profile:[/yellow]")
        profile_path = output.with_suffix('.profile.json')
        profiler.save_results(profile_path)
        console.print(f"  Profile saved to: {profile_path}")