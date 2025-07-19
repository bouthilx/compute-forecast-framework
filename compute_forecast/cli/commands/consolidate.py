import typer
from pathlib import Path
import json
from datetime import datetime
from typing import Optional, List
import logging
import uuid
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.live import Live
import sys
import io

from compute_forecast.pipeline.consolidation.sources.semantic_scholar import SemanticScholarSource
from compute_forecast.pipeline.consolidation.sources.openalex import OpenAlexSource
from compute_forecast.pipeline.consolidation.sources.base import SourceConfig
from compute_forecast.pipeline.consolidation.sources.logging_wrapper import LoggingSourceWrapper
from compute_forecast.pipeline.consolidation.checkpoint_manager import ConsolidationCheckpointManager
from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.utils.profiling import PerformanceProfiler, set_profiler, profile_operation
from compute_forecast.cli.utils.logging_handler import RichConsoleHandler

console = Console()
logger = logging.getLogger(__name__)


def load_papers(input_path: Path) -> List[Paper]:
    """Load papers from collected JSON file"""
    with open(input_path) as f:
        data = json.load(f)
    
    papers = []
    for i, paper_data in enumerate(data.get("papers", [])):
        # Convert to Paper object
        paper = Paper.from_dict(paper_data)
        
        # Generate a unique ID if none exists
        if not paper.paper_id:
            # Use a combination of venue, year, and index as temporary ID
            paper.paper_id = f"{paper.venue}_{paper.year}_{i:04d}"
            
        papers.append(paper)
        
    return papers


def save_papers(papers: List[Paper], output_path: Path, stats: dict):
    """Save enriched papers to JSON file"""
    # Convert papers to dict format with proper serialization
    papers_data = []
    for p in papers:
        # to_dict() now handles all serialization including provenance records
        paper_dict = p.to_dict()
        papers_data.append(paper_dict)
    
    output_data = {
        "consolidation_metadata": {
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
        },
        "papers": papers_data
    }
    
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)


def main(
    input: Path = typer.Option(..., "--input", "-i", help="Input JSON file from collect"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    enrich: Optional[str] = typer.Option("citations,abstracts", "--enrich", help="Fields to enrich"),
    sources: Optional[str] = typer.Option("semantic_scholar,openalex", "--sources", help="Sources to use"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable progress bars"),
    parallel: int = typer.Option(1, "--parallel", help="Number of parallel workers"),
    ss_api_key: Optional[str] = typer.Option(None, "--ss-api-key", help="Semantic Scholar API key", envvar="SEMANTIC_SCHOLAR_API_KEY"),
    openalex_email: Optional[str] = typer.Option(None, "--openalex-email", help="OpenAlex email", envvar="OPENALEX_EMAIL"),
    profile: bool = typer.Option(False, "--profile", help="Enable performance profiling"),
    resume: bool = typer.Option(False, "--resume", help="Resume from previous checkpoint if available"),
    checkpoint_interval: float = typer.Option(5.0, "--checkpoint-interval", help="Minutes between checkpoints (0 to disable)"),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True, help="Increase verbosity level (-v for INFO, -vv for DEBUG)"),
):
    """
    Consolidate and enrich paper metadata from multiple sources.
    
    Examples:
        cf consolidate --input papers.json --output enriched.json
        cf consolidate --input papers.json --enrich citations
        cf consolidate --input papers.json --sources semantic_scholar
        cf consolidate --input papers.json --resume  # Resume from checkpoint
        cf consolidate --input papers.json -v     # INFO level logging
        cf consolidate --input papers.json -vv    # DEBUG level logging
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
    
    # Parse options
    enrich_fields = [f.strip() for f in enrich.split(",")]
    source_names = [s.strip() for s in sources.split(",")]
    
    # Handle session management for resume
    session_id = None
    if resume:
        # Try to find existing session for this input file
        session_id = ConsolidationCheckpointManager.get_latest_resumable_session(str(input))
        if session_id:
            console.print(f"[cyan]Found resumable session: {session_id}[/cyan]")
        else:
            # Check if there are any resumable sessions
            sessions = ConsolidationCheckpointManager.find_resumable_sessions()
            if sessions:
                console.print("[yellow]No resumable session found for this input file.[/yellow]")
                console.print("\nAvailable sessions:")
                for s in sessions[:5]:  # Show last 5
                    console.print(f"  • {s['session_id']} - {s['input_file']} ({s['status']})")
                if not typer.confirm("\nStart a new session?"):
                    return
    
    # Initialize checkpoint manager (will generate session ID if needed)
    checkpoint_manager = ConsolidationCheckpointManager(
        session_id=session_id,
        checkpoint_interval_minutes=checkpoint_interval
    )
    
    # Initialize sources state tracking
    sources_state = {name: {
        "status": "pending",
        "batches_completed": 0,
        "total_batches": 0,
        "papers_processed": 0,
        "enrichments": {
            "citations": 0,
            "abstracts": 0,
            "urls": 0,
            "identifiers": 0
        }
    } for name in source_names}
    
    # Check for resume
    checkpoint_data = None
    if resume:
        checkpoint_result = checkpoint_manager.load_checkpoint()
        if checkpoint_result:
            checkpoint_data, papers = checkpoint_result
            console.print(f"[green]Resuming from checkpoint: {checkpoint_data.session_id}[/green]")
            console.print(f"  Papers loaded: {len(papers)}")
            console.print(f"  Sources state: {list(checkpoint_data.sources.keys())}")
            
            # Restore sources state (only for requested sources)
            saved_sources = checkpoint_data.sources
            for name in source_names:
                if name in saved_sources:
                    sources_state[name] = saved_sources[name]
                else:
                    # New source added since checkpoint
                    console.print(f"[yellow]Note: Source '{name}' was not in the original run[/yellow]")
            
            # Check for sources that were in checkpoint but not requested now
            removed_sources = set(saved_sources.keys()) - set(source_names)
            if removed_sources:
                console.print(f"[yellow]Warning: Sources {removed_sources} were in checkpoint but not requested now[/yellow]")
            
            # Validate input file matches
            if str(input) != checkpoint_data.input_file:
                console.print(f"[yellow]Warning: Input file changed from {checkpoint_data.input_file} to {input}[/yellow]")
                if not typer.confirm("Continue with resume anyway?"):
                    return
                    
            # Validate paper count hasn't changed dramatically
            if checkpoint_data.total_papers != len(papers):
                diff = abs(checkpoint_data.total_papers - len(papers))
                console.print(f"[yellow]Warning: Paper count changed from {checkpoint_data.total_papers} to {len(papers)} (diff: {diff})[/yellow]")
                if diff > checkpoint_data.total_papers * 0.1:  # More than 10% change
                    console.print("[red]Paper count changed by more than 10% - this might indicate a different dataset[/red]")
                    if not typer.confirm("Continue anyway?"):
                        return
        else:
            console.print("[yellow]No valid checkpoint found, starting fresh[/yellow]")
    
    # Load papers if not resuming
    if not checkpoint_data:
        console.print(f"[cyan]Loading papers from {input}...[/cyan]")
        with profile_operation('load_papers', file=str(input)):
            papers = load_papers(input)
        console.print(f"[green]Loaded {len(papers)} papers[/green]")
    
    if dry_run:
        console.print("\n[yellow]DRY RUN - Would enrich:[/yellow]")
        console.print(f"  Fields: {', '.join(enrich_fields)}")
        console.print(f"  Sources: {', '.join(source_names)}")
        console.print(f"  Papers: {len(papers)}")
        return
    
    # Initialize sources
    source_objects = []
    
    if "semantic_scholar" in source_names:
        config = SourceConfig(api_key=ss_api_key)
        # Note: SemanticScholarSource automatically configures:
        # - Without API key: 0.1 req/sec (conservative for shared pool)
        # - With API key: 1.0 req/sec (introductory rate)
        # - Batch sizes: 500 papers (API maximum)
        source_objects.append(SemanticScholarSource(config))
        
    if "openalex" in source_names:
        config = SourceConfig(api_key=openalex_email)  # Email in api_key field
        source_objects.append(OpenAlexSource(config))
    
    # Wrap sources with logging
    logged_sources = []
    for source in source_objects:
        logged_source = LoggingSourceWrapper(source)
        logged_sources.append(logged_source)
    source_objects = logged_sources
    
    # Track statistics
    stats = {
        "total_papers": len(papers),
        "citations_added": 0,
        "abstracts_added": 0,
        "urls_added": 0,
        "identifiers_added": 0,
        "api_calls": {}
    }
    
    # Create paper lookup for efficient updates
    papers_by_id = {p.paper_id: p for p in papers if p.paper_id}
    
    # Track timing for better ETA calculation
    import time
    
    # Create progress bars
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[cyan]{task.fields[time_remaining]}[/cyan]"),
        TextColumn(
            "• {task.fields[citations_pct]:.1f}% citations • {task.fields[abstracts_pct]:.1f}% abstracts • {task.fields[urls_pct]:.1f}% URLs • {task.fields[identifiers_pct]:.1f}% IDs"
        ),
        console=console,
        disable=no_progress,
    )
    
    # Set up custom logging handler that works with Live display
    with Live(progress, console=console, refresh_per_second=4, vertical_overflow="visible", transient=True) as live:
        # Add our custom handler to root logger
        rich_handler = RichConsoleHandler(console, live)
        rich_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(rich_handler)
        
        # Log initial info
        logger.info(f"Starting consolidation with {len(papers)} papers from {len(source_objects)} sources")
        
        # Create a progress task for each source
        source_tasks = {}
        for source in source_objects:
            task_id = progress.add_task(
                f"[cyan]{source.name}[/cyan]",
                total=len(papers),
                citations_added=0,
                abstracts_added=0,
                urls_added=0,
                identifiers_added=0,
                citations_pct=0.0,
                abstracts_pct=0.0,
                urls_pct=0.0,
                identifiers_pct=0.0,
                time_remaining="",
            )
            source_tasks[source.name] = task_id
        
        for source in source_objects:
            # Skip completed sources if resuming
            if sources_state[source.name]["status"] == "completed":
                task_id = source_tasks[source.name]
                progress.update(task_id, completed=len(papers))
                logger.info(f"Skipping completed source: {source.name}")
                continue
                
            task_id = source_tasks[source.name]
            
            # Update source status
            sources_state[source.name]["status"] = "in_progress"
            
            # Calculate total batches for this source
            batch_size = source.config.find_batch_size or source.config.batch_size
            total_batches = (len(papers) + batch_size - 1) // batch_size
            sources_state[source.name]["total_batches"] = total_batches
            
            # Log source start
            logger.info(f"Starting {source.name} - {total_batches} batches @ {batch_size} papers/batch")
            logger.info(f"Rate limit: {source.config.rate_limit:.2f} req/s, API key: {'Yes' if source.config.api_key else 'No'}")
            
            # Restore progress if resuming
            if checkpoint_data and source.name in sources_state and sources_state[source.name]["status"] != "pending":
                source_state = sources_state[source.name]
                papers_processed = source_state["papers_processed"]
                source_citations = source_state["enrichments"]["citations"]
                source_abstracts = source_state["enrichments"]["abstracts"] 
                source_urls = source_state["enrichments"]["urls"]
                source_identifiers = source_state["enrichments"]["identifiers"]
                
                # Update progress bar to resumed position
                progress.update(task_id, completed=papers_processed)
                
                # Show resume statistics
                console.print(f"[dim]  Resuming with: {papers_processed} papers processed, "
                            f"{source_citations} citations, {source_abstracts} abstracts, "
                            f"{source_urls} URLs, {source_identifiers} identifiers[/dim]")
                
                # Adjust start time to account for previous processing
                # This gives more accurate ETA calculations
                if papers_processed > 0 and batch_size > 0:
                    # Estimate previous processing time based on checkpoint interval
                    estimated_previous_time = (papers_processed / batch_size) * 30  # Rough estimate
                    start_time = time.time() - estimated_previous_time
                else:
                    start_time = time.time()
            else:
                # Track statistics for this source
                source_citations = 0
                source_abstracts = 0
                source_urls = 0
                source_identifiers = 0
                papers_processed = 0
                start_time = time.time()
            
            def update_progress(result):
                nonlocal source_citations, source_abstracts, source_urls, source_identifiers, papers_processed
                
                # Apply enrichments to papers
                if result.paper_id in papers_by_id:
                    paper = papers_by_id[result.paper_id]
                    
                    # Use merge to avoid duplicates (important for resume)
                    checkpoint_manager.merge_enrichments(paper, result)
                    
                    # Track statistics for this source
                    source_citations += len(result.citations)
                    source_abstracts += len(result.abstracts)
                    source_urls += len(result.urls)
                    source_identifiers += len(result.identifiers)
                
                papers_processed += 1
                
                # Calculate percentages based on papers processed so far
                citations_pct = (source_citations / papers_processed * 100) if papers_processed > 0 else 0.0
                abstracts_pct = (source_abstracts / papers_processed * 100) if papers_processed > 0 else 0.0
                urls_pct = (source_urls / papers_processed * 100) if papers_processed > 0 else 0.0
                identifiers_pct = (source_identifiers / papers_processed * 100) if papers_processed > 0 else 0.0
                
                # Calculate custom ETA based on actual processing rate
                elapsed = time.time() - start_time
                if papers_processed > 0 and elapsed > 0:
                    rate = papers_processed / elapsed  # papers per second
                    remaining_papers = len(papers) - papers_processed
                    if rate > 0:
                        remaining_seconds = remaining_papers / rate
                        # Format as HH:MM:SS
                        hours, remainder = divmod(int(remaining_seconds), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        if hours > 0:
                            time_remaining = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        else:
                            time_remaining = f"{minutes:02d}:{seconds:02d}"
                    else:
                        time_remaining = "--:--"
                else:
                    time_remaining = "--:--"
                
                # Update progress for this paper in this source
                progress.update(
                    task_id,
                    advance=1,
                    citations_added=source_citations,
                    abstracts_added=source_abstracts,
                    urls_added=source_urls,
                    identifiers_added=source_identifiers,
                    citations_pct=citations_pct,
                    abstracts_pct=abstracts_pct,
                    urls_pct=urls_pct,
                    identifiers_pct=identifiers_pct,
                    time_remaining=time_remaining,
                )
            
            try:
                # Custom batch processing with checkpoint support
                batch_size = source.config.find_batch_size or source.config.batch_size
                
                # Determine starting batch if resuming
                start_batch = 0
                if checkpoint_data and source.name in sources_state:
                    batches_completed = sources_state[source.name]["batches_completed"]
                    start_batch = batches_completed
                    console.print(f"[cyan]Resuming {source.name} from batch {start_batch + 1}/{total_batches}[/cyan]")
                
                # Process papers in batches with checkpoint support
                batch_start_idx = start_batch * batch_size
                
                # Validate resume position
                if batch_start_idx >= len(papers):
                    console.print(f"[yellow]Warning: Resume position beyond paper count for {source.name}, starting from beginning[/yellow]")
                    batch_start_idx = 0
                    start_batch = 0
                    sources_state[source.name]["batches_completed"] = 0
                
                for batch_idx, i in enumerate(range(batch_start_idx, len(papers), batch_size)):
                    batch = papers[i:i + batch_size]
                    actual_batch_idx = start_batch + batch_idx
                    
                    # Log batch start
                    logger.info(f"Starting batch {actual_batch_idx + 1}/{total_batches} ({len(batch)} papers)")
                    
                    try:
                        # Call the source's enrich_papers for this batch
                        logger.debug(f"Calling {source.name}.enrich_papers() for batch...")
                        
                        batch_results = source.enrich_papers(batch, progress_callback=update_progress)
                        
                        # Update batch completion only after successful processing
                        sources_state[source.name]["batches_completed"] = actual_batch_idx + 1
                        sources_state[source.name]["papers_processed"] = min(i + len(batch), len(papers))
                        sources_state[source.name]["enrichments"]["citations"] = source_citations
                        sources_state[source.name]["enrichments"]["abstracts"] = source_abstracts
                        sources_state[source.name]["enrichments"]["urls"] = source_urls
                        sources_state[source.name]["enrichments"]["identifiers"] = source_identifiers
                        
                        # Check if we should checkpoint
                        checkpoint_saved = checkpoint_manager.save_checkpoint(
                            input_file=str(input),
                            total_papers=len(papers),
                            sources_state=sources_state,
                            papers=papers,
                            force=False  # Will only save if 5+ minutes elapsed
                        )
                        
                        if checkpoint_saved:
                            logger.info(f"✓ Checkpoint saved at batch {actual_batch_idx + 1}/{total_batches}")
                            
                    except Exception as e:
                        logger.error(f"Error processing batch {actual_batch_idx + 1} for {source.name}: {e}")
                        console.print(f"[red]Error in batch {actual_batch_idx + 1}: {e}[/red]")
                        
                        # Save checkpoint before re-raising
                        checkpoint_manager.save_checkpoint(
                            input_file=str(input),
                            total_papers=len(papers),
                            sources_state=sources_state,
                            papers=papers,
                            force=True
                        )
                        raise
                
                # Mark source as completed
                sources_state[source.name]["status"] = "completed"
                
                # Log source completion
                logger.info(f"✓ Completed {source.name}: +{source_citations} citations, "
                           f"+{source_abstracts} abstracts, +{source_urls} URLs, +{source_identifiers} identifiers")
                
                # Force checkpoint after source completion
                checkpoint_manager.save_checkpoint(
                    input_file=str(input),
                    total_papers=len(papers),
                    sources_state=sources_state,
                    papers=papers,
                    force=True
                )
                
                logger.info(f"✓ Checkpoint saved after {source.name} completion")
                
                # Update global statistics
                stats["citations_added"] += source_citations
                stats["abstracts_added"] += source_abstracts
                stats["urls_added"] += source_urls
                stats["identifiers_added"] += source_identifiers
                
                # Mark as completed
                progress.update(task_id, time_remaining="done")
                
            except Exception as e:
                logger.error(f"Error enriching from {source.name}: {e}")
                console.print(f"[red]✗[/red] Failed to enrich from {source.name}: {e}")
                
                # Update source status
                sources_state[source.name]["status"] = "failed"
                
                # Save checkpoint on error
                checkpoint_manager.save_checkpoint(
                    input_file=str(input),
                    total_papers=len(papers),
                    sources_state=sources_state,
                    papers=papers,
                    force=True
                )
                
                # Complete the progress bar even on failure
                progress.update(task_id, completed=len(papers))
    
    # Collect API call stats
    for source in source_objects:
        stats["api_calls"][source.name] = source.api_calls
    
    # Save results
    output.parent.mkdir(parents=True, exist_ok=True)
    with profile_operation('save_papers', file=str(output)):
        save_papers(papers, output, stats)
    
    console.print(f"\n[green]✓[/green] Saved enriched data to {output}")
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Papers processed: {stats['total_papers']}")
    console.print(f"  Citations added: {stats['citations_added']}")
    console.print(f"  Abstracts added: {stats['abstracts_added']}")
    console.print(f"  URLs added: {stats['urls_added']}")
    console.print(f"  Identifiers added: {stats['identifiers_added']}")
    console.print(f"  API calls: {sum(stats['api_calls'].values())}")
    
    # Clean up checkpoint files after successful completion
    checkpoint_manager.cleanup()
    
    # Print profiling report if enabled
    if profile:
        profiler.print_report()
        
        # Also save detailed breakdown
        breakdown = profiler.get_detailed_breakdown()
        profile_path = output.parent / f"profile_{output.stem}.json"
        with open(profile_path, "w") as f:
            json.dump({
                'summary': profiler.get_summary(),
                'breakdown': breakdown,
                'records': [
                    {
                        'name': r.name,
                        'duration': r.duration,
                        'metadata': r.metadata
                    }
                    for r in profiler.records if r.duration
                ]
            }, f, indent=2)
        console.print(f"\n[dim]Detailed profile saved to {profile_path}[/dim]")