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
from compute_forecast.pipeline.consolidation.enrichment.citation_enricher import CitationEnricher
from compute_forecast.pipeline.consolidation.enrichment.abstract_enricher import AbstractEnricher
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
        paper_dict = p.to_dict()
        
        # Convert CitationRecord objects to dicts
        if hasattr(p, 'citations_history') and p.citations_history:
            paper_dict['citations_history'] = [
                {
                    "source": record.source,
                    "timestamp": record.timestamp.isoformat(),
                    "data": {"count": record.data.count}
                }
                for record in p.citations_history
            ]
            
        # Convert AbstractRecord objects to dicts
        if hasattr(p, 'abstracts_history') and p.abstracts_history:
            paper_dict['abstracts_history'] = [
                {
                    "source": record.source,
                    "timestamp": record.timestamp.isoformat(),
                    "data": {
                        "text": record.data.text,
                        "language": record.data.language
                    }
                }
                for record in p.abstracts_history
            ]
            
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
        "api_calls": {}
    }
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Enrich citations
        if "citations" in enrich_fields:
            task = progress.add_task("Enriching citations...", total=None)
            
            enricher = CitationEnricher(source_objects)
            citation_records = enricher.enrich(papers)
            
            # Update papers
            for paper in papers:
                if paper.paper_id in citation_records:
                    paper.citations_history.extend(citation_records[paper.paper_id])
                    stats["citations_added"] += len(citation_records[paper.paper_id])
                    
            progress.update(task, completed=True)
            console.print(f"[green]✓[/green] Added {stats['citations_added']} citation records")
        
        # Enrich abstracts
        if "abstracts" in enrich_fields:
            task = progress.add_task("Enriching abstracts...", total=None)
            
            enricher = AbstractEnricher(source_objects)
            abstract_records = enricher.enrich(papers)
            
            # Update papers
            for paper in papers:
                if paper.paper_id in abstract_records:
                    paper.abstracts_history.extend(abstract_records[paper.paper_id])
                    stats["abstracts_added"] += len(abstract_records[paper.paper_id])
                    
            progress.update(task, completed=True)
            console.print(f"[green]✓[/green] Added {stats['abstracts_added']} abstract records")
    
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
    console.print(f"  API calls: {sum(stats['api_calls'].values())}")