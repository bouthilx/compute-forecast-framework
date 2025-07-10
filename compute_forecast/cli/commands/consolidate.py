import typer
from pathlib import Path
import json
from datetime import datetime
from typing import Optional, List
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

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
        console=console,
    ) as progress:
        
        # Single enrichment pass through all sources
        task = progress.add_task("Enriching papers from all sources...", total=len(source_objects))
        
        for source in source_objects:
            console.print(f"[cyan]Enriching from {source.name}...[/cyan]")
            
            try:
                # Get ALL enrichment data in one pass
                enrichment_results = source.enrich_papers(papers)
                
                # Apply all enrichments to papers
                for result in enrichment_results:
                    if result.paper_id in papers_by_id:
                        paper = papers_by_id[result.paper_id]
                        
                        # Add all enrichment data with provenance
                        paper.citations.extend(result.citations)
                        paper.abstracts.extend(result.abstracts)
                        paper.urls.extend(result.urls)
                        
                        # Update statistics
                        stats["citations_added"] += len(result.citations)
                        stats["abstracts_added"] += len(result.abstracts)
                        stats["urls_added"] += len(result.urls)
                
                console.print(f"[green]✓[/green] Completed {source.name}")
                
            except Exception as e:
                logger.error(f"Error enriching from {source.name}: {e}")
                console.print(f"[red]✗[/red] Failed to enrich from {source.name}: {e}")
            
            progress.advance(task)
    
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