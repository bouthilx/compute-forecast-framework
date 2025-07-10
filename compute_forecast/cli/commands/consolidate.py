import typer
from pathlib import Path
import json
from datetime import datetime
from typing import Optional, List
import logging
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)

from compute_forecast.pipeline.consolidation.sources.semantic_scholar import SemanticScholarSource
from compute_forecast.pipeline.consolidation.sources.openalex import OpenAlexSource
from compute_forecast.pipeline.consolidation.sources.base import SourceConfig
from compute_forecast.pipeline.metadata_collection.models import Paper

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
):
    """
    Consolidate and enrich paper metadata from multiple sources.
    
    Examples:
        cf consolidate --input papers.json --output enriched.json
        cf consolidate --input papers.json --enrich citations
        cf consolidate --input papers.json --sources semantic_scholar
    """
    
    # Set default output
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = Path(f"data/consolidated_papers/papers_{timestamp}.json")
    
    # Parse options
    enrich_fields = [f.strip() for f in enrich.split(",")]
    source_names = [s.strip() for s in sources.split(",")]
    
    console.print(f"[cyan]Loading papers from {input}...[/cyan]")
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
        source_objects.append(SemanticScholarSource(config))
        
    if "openalex" in source_names:
        config = SourceConfig(api_key=openalex_email)  # Email in api_key field
        source_objects.append(OpenAlexSource(config))
    
    # Track statistics
    stats = {
        "total_papers": len(papers),
        "citations_added": 0,
        "abstracts_added": 0,
        "urls_added": 0,
        "api_calls": {}
    }
    
    # Create paper lookup for efficient updates
    papers_by_id = {p.paper_id: p for p in papers if p.paper_id}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        TextColumn(
            "• {task.fields[citations_pct]:.1f}% citations • {task.fields[abstracts_pct]:.1f}% abstracts • {task.fields[urls_pct]:.1f}% URLs"
        ),
        console=console,
        disable=no_progress,
    ) as progress:
        
        # Create a progress task for each source
        source_tasks = {}
        for source in source_objects:
            task_id = progress.add_task(
                f"[cyan]{source.name}[/cyan]",
                total=len(papers),
                citations_added=0,
                abstracts_added=0,
                urls_added=0,
                citations_pct=0.0,
                abstracts_pct=0.0,
                urls_pct=0.0,
            )
            source_tasks[source.name] = task_id
        
        for source in source_objects:
            task_id = source_tasks[source.name]
            
            # Track statistics for this source
            source_citations = 0
            source_abstracts = 0
            source_urls = 0
            papers_processed = 0
            
            def update_progress(result):
                nonlocal source_citations, source_abstracts, source_urls, papers_processed
                
                # Apply enrichments to papers
                if result.paper_id in papers_by_id:
                    paper = papers_by_id[result.paper_id]
                    
                    # Add all enrichment data with provenance
                    paper.citations.extend(result.citations)
                    paper.abstracts.extend(result.abstracts)
                    paper.urls.extend(result.urls)
                    
                    # Track statistics for this source
                    source_citations += len(result.citations)
                    source_abstracts += len(result.abstracts)
                    source_urls += len(result.urls)
                
                papers_processed += 1
                
                # Calculate percentages based on papers processed so far
                citations_pct = (source_citations / papers_processed * 100) if papers_processed > 0 else 0.0
                abstracts_pct = (source_abstracts / papers_processed * 100) if papers_processed > 0 else 0.0
                urls_pct = (source_urls / papers_processed * 100) if papers_processed > 0 else 0.0
                
                # Update progress for this paper in this source
                progress.update(
                    task_id,
                    advance=1,
                    citations_added=source_citations,
                    abstracts_added=source_abstracts,
                    urls_added=source_urls,
                    citations_pct=citations_pct,
                    abstracts_pct=abstracts_pct,
                    urls_pct=urls_pct,
                )
            
            try:
                # Get ALL enrichment data with progress tracking
                enrichment_results = source.enrich_papers(papers, progress_callback=update_progress)
                
                # Update global statistics
                stats["citations_added"] += source_citations
                stats["abstracts_added"] += source_abstracts
                stats["urls_added"] += source_urls
                
                console.print(f"[green]✓[/green] Completed {source.name}: +{source_citations} citations, +{source_abstracts} abstracts, +{source_urls} URLs")
                
            except Exception as e:
                logger.error(f"Error enriching from {source.name}: {e}")
                console.print(f"[red]✗[/red] Failed to enrich from {source.name}: {e}")
                
                # Complete the progress bar even on failure
                progress.update(task_id, completed=len(papers))
    
    # Collect API call stats
    for source in source_objects:
        stats["api_calls"][source.name] = source.api_calls
    
    # Save results
    output.parent.mkdir(parents=True, exist_ok=True)
    save_papers(papers, output, stats)
    
    console.print(f"\n[green]✓[/green] Saved enriched data to {output}")
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Papers processed: {stats['total_papers']}")
    console.print(f"  Citations added: {stats['citations_added']}")
    console.print(f"  Abstracts added: {stats['abstracts_added']}")
    console.print(f"  URLs added: {stats['urls_added']}")
    console.print(f"  API calls: {sum(stats['api_calls'].values())}")