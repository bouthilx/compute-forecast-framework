import typer
from pathlib import Path
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Set
import logging
import requests
import time
import re
import hashlib
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    ProgressColumn,
    Task,
)
from rich.text import Text
from rich.live import Live

from compute_forecast.pipeline.consolidation.sources.semantic_scholar import (
    SemanticScholarSource,
)
from compute_forecast.pipeline.consolidation.sources.openalex import OpenAlexSource
from compute_forecast.pipeline.consolidation.sources.base import SourceConfig
from compute_forecast.pipeline.consolidation.sources.logging_wrapper import (
    LoggingSourceWrapper,
)
from compute_forecast.pipeline.consolidation.checkpoint_manager import (
    ConsolidationCheckpointManager,
)
from compute_forecast.pipeline.consolidation.models_extended import (
    PaperIdentifiers,
    ConsolidationPhaseState,
)
from compute_forecast.pipeline.consolidation.models import EnrichmentResult
from compute_forecast.pipeline.metadata_collection.models import Paper
from compute_forecast.utils.profiling import (
    PerformanceProfiler,
    set_profiler,
    profile_operation,
)
from compute_forecast.cli.utils.logging_handler import RichConsoleHandler

console = Console()
logger = logging.getLogger(__name__)


def get_paper_hash(paper: Paper) -> str:
    """Generate a unique hash for a paper based on title, authors, venue, and year."""
    # Normalize title
    title = paper.title.lower().strip() if paper.title else ""

    # Sort and normalize author names
    authors = []
    if hasattr(paper, "authors") and paper.authors:
        for author in paper.authors:
            if isinstance(author, dict):
                name = author.get("name", "").lower().strip()
            else:
                name = str(author).lower().strip()
            if name:
                authors.append(name)
    authors.sort()
    authors_str = ";".join(authors)

    # Normalize venue
    venue = paper.venue.lower().strip() if paper.venue else ""

    # Year
    year = str(paper.year) if paper.year else ""

    # Create hash
    content = f"{title}|{authors_str}|{venue}|{year}"
    return hashlib.sha256(content.encode()).hexdigest()


class DetailedProgressColumn(ProgressColumn):
    """Custom progress column showing: <progress>%, (<n done>/<total>) DD HH:MM:SS (YYYY-MM-DD HH:MM:SS ETA)"""

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

        # Format the complete string
        text = f"{percentage:5.1f}%, ({task.completed}/{task.total}) {elapsed_str} ({eta_str} ETA)"

        return Text(text, style="cyan")


class Phase1ProgressColumn(ProgressColumn):
    """Custom progress column for Phase 1 showing ID type percentages"""

    def __init__(self):
        self.identifiers = {}
        super().__init__()

    def set_identifiers(self, identifiers_dict: Dict[str, PaperIdentifiers]):
        """Update the identifiers dictionary reference"""
        self.identifiers = identifiers_dict

    def render(self, task: Task) -> Text:
        """Render the progress details with ID type percentages."""
        if task.total is None or task.total == 0:
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

        # Calculate ID type counts
        doi_count = sum(1 for ids in self.identifiers.values() if ids.doi)
        arxiv_count = sum(1 for ids in self.identifiers.values() if ids.arxiv_id)
        oa_count = sum(1 for ids in self.identifiers.values() if ids.openalex_id)
        s2_count = sum(
            1 for ids in self.identifiers.values() if ids.semantic_scholar_id
        )
        pmid_count = sum(1 for ids in self.identifiers.values() if ids.pmid)

        # Format the complete string
        text = f"{percentage:5.1f}% ({task.completed}/{task.total}) {elapsed_str} ({eta_str}) [DOI:{doi_count} ArXiv:{arxiv_count} OA:{oa_count} S2:{s2_count} PM:{pmid_count}]"

        return Text(text, style="cyan")


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
            "method": "two-phase",
            "phases": [
                "openalex_id_harvesting",
                "semantic_scholar_batch_enrichment",
                "openalex_full_enrichment",
            ],
        },
        "papers": papers_data,
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)


def harvest_identifiers_openalex(
    papers: List[Paper],
    openalex_source: OpenAlexSource,
    progress_callback=None,
    checkpoint_callback=None,
    existing_identifiers: Optional[Dict[str, PaperIdentifiers]] = None,
    processed_hashes: Optional[Set[str]] = None,
    batch_size: int = 1,
) -> Dict[str, PaperIdentifiers]:
    """
    Phase 1: Fast first-pass to collect all identifiers using OpenAlex.

    Args:
        papers: List of papers to process
        openalex_source: OpenAlex source instance
        progress_callback: Optional callback(count) for progress updates
        checkpoint_callback: Optional callback(identifiers, hashes) for checkpointing
        existing_identifiers: Optional dict of already processed identifiers for resume
        processed_hashes: Optional set of already processed paper hashes
        batch_size: Batch size for processing papers (default 1 for title searches)

    Returns mapping of paper_id -> PaperIdentifiers
    """
    identifiers = existing_identifiers or {}
    processed_hashes = processed_hashes or set()

    # Filter out papers we've already processed based on hash
    papers_to_process = []
    skipped_count = 0
    for p in papers:
        paper_hash = get_paper_hash(p)
        if paper_hash not in processed_hashes:
            papers_to_process.append(p)
        else:
            skipped_count += 1
            # Paper already processed, update progress
            if progress_callback:
                progress_callback(1)

    logger.info(
        f"Skipping {skipped_count} papers already processed (hashes: {len(processed_hashes)})"
    )

    if not papers_to_process:
        logger.info("All papers already have identifiers from checkpoint")
        return identifiers

    # First, use find_papers to get OpenAlex IDs
    logger.info("Finding papers in OpenAlex...")

    # Process in batches for find_papers
    # Use the batch_size parameter passed to the function, not the config value
    oa_mapping = {}

    for i in range(0, len(papers_to_process), batch_size):
        batch = papers_to_process[i : i + batch_size]
        batch_mapping = openalex_source.find_papers(batch)
        oa_mapping.update(batch_mapping)

        # Create PaperIdentifiers for papers found in OpenAlex
        for paper_id, oa_id in batch_mapping.items():
            if oa_id and paper_id not in identifiers:
                identifiers[paper_id] = PaperIdentifiers(
                    paper_id=paper_id, openalex_id=oa_id
                )

        if progress_callback:
            progress_callback(len(batch))

        # Mark ALL papers in batch as processed (found or not)
        for paper in batch:
            processed_hashes.add(get_paper_hash(paper))

        if checkpoint_callback:
            checkpoint_callback(identifiers, processed_hashes)

    logger.info(f"Found {len(oa_mapping)} papers in OpenAlex")

    # Now fetch minimal data to extract identifiers
    if oa_mapping:
        # We need to fetch just the identifiers from OpenAlex
        # Use a custom select to minimize data transfer
        select_fields = "id,ids,doi,primary_location"

        oa_ids = list(oa_mapping.values())

        # Process in batches
        for i in range(0, len(oa_ids), batch_size):
            batch_ids = oa_ids[i : i + batch_size]

            # Build filter string
            filter_str = "openalex:" + "|".join(batch_ids)

            openalex_source._rate_limit()
            response = requests.get(
                f"{openalex_source.base_url}/works",
                params={
                    "filter": filter_str,
                    "per-page": len(batch_ids),
                    "select": select_fields,
                },
                headers=openalex_source.headers,
            )
            openalex_source.api_calls += 1

            if response.status_code == 200:
                for work in response.json().get("results", []):
                    work_id = work.get("id")
                    if not work_id:
                        continue

                    # Find which paper this corresponds to
                    paper_id = None
                    for pid, oa_id in oa_mapping.items():
                        if oa_id == work_id:
                            paper_id = pid
                            break

                    if not paper_id:
                        continue

                    # Extract identifiers
                    ids = work.get("ids", {})

                    # Extract ArXiv ID from various sources
                    arxiv_id = None

                    # Method 1: Check if DOI contains arxiv
                    doi = ids.get("doi", "")
                    if "arxiv" in doi.lower():
                        match = re.search(r"arxiv\.(\d{4}\.\d{4,5})", doi.lower())
                        if match:
                            arxiv_id = match.group(1)

                    # Method 2: Check primary location
                    if not arxiv_id:
                        primary_loc = work.get("primary_location", {})
                        landing_url = primary_loc.get("landing_page_url", "")
                        pdf_url = primary_loc.get("pdf_url", "")

                        # Check if it's an ArXiv URL
                        for url in [landing_url, pdf_url]:
                            if url and "arxiv.org" in url:
                                # Extract ArXiv ID from URL like https://arxiv.org/abs/1706.03762
                                # Handle both old format (1234.5678) and new format (2301.12345)
                                match = re.search(
                                    r"arxiv\.org/(?:pdf|abs)/(\d{4}\.\d{4,5})", url
                                )
                                if match:
                                    arxiv_id = match.group(1)
                                    break

                    # Method 3: Check all locations
                    if not arxiv_id:
                        for location in work.get("locations", []):
                            landing_url = location.get("landing_page_url", "")
                            if landing_url and "arxiv.org" in landing_url:
                                match = re.search(
                                    r"arxiv\.org/(?:pdf|abs)/(\d{4}\.\d{4,5})",
                                    landing_url,
                                )
                                if match:
                                    arxiv_id = match.group(1)
                                    break

                    # Update existing PaperIdentifiers object or create new one
                    if paper_id in identifiers:
                        paper_ids = identifiers[paper_id]
                        # Update with additional identifiers
                        if ids.get("doi"):
                            paper_ids.doi = ids.get("doi", "").replace(
                                "https://doi.org/", ""
                            )
                        if arxiv_id:
                            paper_ids.arxiv_id = arxiv_id
                        if ids.get("pmid"):
                            # Extract PMID number from URL like https://pubmed.ncbi.nlm.nih.gov/34265844
                            pmid = str(ids.get("pmid"))
                            if "pubmed.ncbi.nlm.nih.gov/" in pmid:
                                paper_ids.pmid = pmid.split("/")[-1]
                            else:
                                paper_ids.pmid = pmid
                        if ids.get("pmcid"):
                            # Extract PMCID from URL like https://www.ncbi.nlm.nih.gov/pmc/articles/8371605
                            pmcid = str(ids.get("pmcid"))
                            if "/pmc/articles/" in pmcid:
                                paper_ids.pmcid = "PMC" + pmcid.split("/")[-1]
                            else:
                                paper_ids.pmcid = pmcid
                        if ids.get("mag"):
                            paper_ids.mag_id = str(ids.get("mag"))
                    else:
                        # Create new PaperIdentifiers object
                        # Extract PMID
                        pmid = None
                        if ids.get("pmid"):
                            pmid = str(ids.get("pmid"))
                            if "pubmed.ncbi.nlm.nih.gov/" in pmid:
                                pmid = pmid.split("/")[-1]

                        # Extract PMCID
                        pmcid = None
                        if ids.get("pmcid"):
                            pmcid = str(ids.get("pmcid"))
                            if "/pmc/articles/" in pmcid:
                                pmcid = "PMC" + pmcid.split("/")[-1]

                        paper_ids = PaperIdentifiers(
                            paper_id=paper_id,
                            openalex_id=work_id,
                            doi=ids.get("doi", "").replace("https://doi.org/", "")
                            if ids.get("doi")
                            else None,
                            arxiv_id=arxiv_id,
                            pmid=pmid,
                            pmcid=pmcid,
                            mag_id=str(ids.get("mag")) if ids.get("mag") else None,
                        )
                        identifiers[paper_id] = paper_ids

            # Add processed papers to hash set
            for paper_id in oa_mapping:
                paper = next((p for p in papers if p.paper_id == paper_id), None)
                if paper:
                    processed_hashes.add(get_paper_hash(paper))

            # Checkpoint after batch if callback provided
            if checkpoint_callback:
                checkpoint_callback(identifiers, processed_hashes)

    return identifiers


def enrich_papers_with_identifiers(
    papers: List[Paper], identifiers: Dict[str, PaperIdentifiers]
) -> List[Paper]:
    """Add discovered identifiers to Paper objects."""
    for paper in papers:
        if paper.paper_id in identifiers:
            ids = identifiers[paper.paper_id]

            # Add identifiers to paper object
            if ids.doi and not paper.doi:
                paper.doi = ids.doi
            if ids.arxiv_id and not paper.arxiv_id:
                paper.arxiv_id = ids.arxiv_id
            if ids.openalex_id and not paper.openalex_id:
                paper.openalex_id = ids.openalex_id

            # Initialize external_ids if needed
            if not hasattr(paper, "external_ids"):
                paper.external_ids = {}

            if ids.semantic_scholar_id:
                paper.external_ids["semantic_scholar"] = ids.semantic_scholar_id
            if ids.pmid:
                paper.external_ids["pmid"] = ids.pmid
            if ids.pmcid:
                paper.external_ids["pmcid"] = ids.pmcid
            if ids.mag_id:
                paper.external_ids["mag"] = ids.mag_id

    return papers


def enrich_semantic_scholar_batch(
    papers: List[Paper],
    identifiers: Dict[str, PaperIdentifiers],
    semantic_scholar_source: SemanticScholarSource,
    progress_callback=None,
    checkpoint_callback=None,
    batch_progress: Optional[Dict[str, Any]] = None,
    processed_hashes: Optional[Set[str]] = None,
    batch_size: int = 500,
) -> Dict[str, Any]:
    """
    Phase 2: Efficient batch enrichment from Semantic Scholar using discovered IDs.

    Returns enrichment statistics.
    """
    stats = {
        "papers_enriched": 0,
        "citations_added": 0,
        "abstracts_added": 0,
        "urls_added": 0,
        "identifiers_added": 0,
    }

    # Build lists of external IDs for batch lookup
    external_ids = []
    id_to_paper = {}
    papers_by_id = {p.paper_id: p for p in papers}
    processed_hashes = processed_hashes or set()

    # Filter out already processed papers
    papers_to_process = []
    skipped_count = 0
    for paper in papers:
        paper_hash = get_paper_hash(paper)
        if paper_hash not in processed_hashes:
            papers_to_process.append(paper)
        else:
            skipped_count += 1
            if progress_callback:
                progress_callback(1)

    logger.info(f"Phase 2: Skipping {skipped_count} papers already processed")

    if not papers_to_process:
        logger.info("All papers already processed in Phase 2")
        return stats

    for paper in papers_to_process:
        paper_ids = identifiers.get(paper.paper_id)
        if not paper_ids:
            # Mark paper as processed even if no IDs
            processed_hashes.add(get_paper_hash(paper))
            continue

        # Add all available external IDs
        if paper_ids.doi:
            external_ids.append(f"DOI:{paper_ids.doi}")
            id_to_paper[f"DOI:{paper_ids.doi}"] = paper.paper_id
        if paper_ids.arxiv_id:
            external_ids.append(f"ARXIV:{paper_ids.arxiv_id}")
            id_to_paper[f"ARXIV:{paper_ids.arxiv_id}"] = paper.paper_id
        if paper_ids.pmid:
            external_ids.append(f"PMID:{paper_ids.pmid}")
            id_to_paper[f"PMID:{paper_ids.pmid}"] = paper.paper_id
        if paper_ids.semantic_scholar_id:
            external_ids.append(paper_ids.semantic_scholar_id)
            id_to_paper[paper_ids.semantic_scholar_id] = paper.paper_id

    if not external_ids:
        logger.warning("No external IDs found for Semantic Scholar lookup")
        return stats

    logger.info(f"Looking up {len(external_ids)} external IDs in Semantic Scholar")

    # Process in batches (S2 API limit is 500)
    for i in range(0, len(external_ids), batch_size):
        batch = external_ids[i : i + batch_size]

        try:
            # Use S2 batch endpoint with retry logic
            max_retries = 3
            retry_delay = 1

            for attempt in range(max_retries):
                try:
                    semantic_scholar_source._rate_limit()
                    response = requests.post(
                        f"{semantic_scholar_source.graph_url}/paper/batch",
                        json={"ids": batch},
                        headers=semantic_scholar_source.headers,
                        params={"fields": "paperId,externalIds"},
                        timeout=30,
                    )
                    semantic_scholar_source.api_calls += 1
                    break  # Success, exit retry loop
                except (
                    ConnectionError,
                    ConnectionResetError,
                    requests.exceptions.Timeout,
                ) as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"S2 connection error on attempt {attempt + 1}/{max_retries}: {str(e)}. "
                            f"Retrying in {retry_delay} seconds..."
                        )
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(
                            f"S2 connection error after {max_retries} attempts: {str(e)}"
                        )
                        raise

            if response.status_code != 200:
                logger.warning(f"Failed to lookup batch: {response.status_code}")
                continue

            # Map external IDs to S2 paper IDs
            s2_ids = []
            s2_to_paper = {}

            for item in response.json():
                if not item or "paperId" not in item:
                    continue

                s2_id = item["paperId"]
                ext_ids = item.get("externalIds", {})

                # Find which paper this corresponds to
                paper_id = None

                # Check DOI
                doi = ext_ids.get("DOI")
                if doi and f"DOI:{doi}" in id_to_paper:
                    paper_id = id_to_paper[f"DOI:{doi}"]
                # Check ArXiv
                elif (
                    ext_ids.get("ArXiv") and f"ARXIV:{ext_ids['ArXiv']}" in id_to_paper
                ):
                    paper_id = id_to_paper[f"ARXIV:{ext_ids['ArXiv']}"]
                # Check PMID
                elif (
                    ext_ids.get("PubMed") and f"PMID:{ext_ids['PubMed']}" in id_to_paper
                ):
                    paper_id = id_to_paper[f"PMID:{ext_ids['PubMed']}"]
                # Check S2 ID directly
                elif s2_id in id_to_paper:
                    paper_id = id_to_paper[s2_id]

                if paper_id:
                    s2_ids.append(s2_id)
                    s2_to_paper[s2_id] = paper_id

            if not s2_ids:
                continue

            # Now fetch full enrichment data
            enrichment_data = semantic_scholar_source.fetch_all_fields(s2_ids)

            # Create EnrichmentResult objects and merge with papers
            for s2_id, data in enrichment_data.items():
                paper_id = s2_to_paper.get(s2_id)
                if not paper_id or paper_id not in papers_by_id:
                    continue

                paper = papers_by_id[paper_id]

                # Create EnrichmentResult
                result = EnrichmentResult(paper_id=paper_id)

                # Add citations
                if data.get("citations") is not None:
                    from compute_forecast.pipeline.consolidation.models import (
                        CitationRecord,
                        CitationData,
                    )

                    citation_record = CitationRecord(
                        source="semantic_scholar",
                        timestamp=datetime.now(),
                        original=False,
                        data=CitationData(count=data["citations"]),
                    )
                    result.citations.append(citation_record)

                # Add abstract
                if data.get("abstract"):
                    from compute_forecast.pipeline.consolidation.models import (
                        AbstractRecord,
                        AbstractData,
                    )

                    abstract_record = AbstractRecord(
                        source="semantic_scholar",
                        timestamp=datetime.now(),
                        original=False,
                        data=AbstractData(text=data["abstract"]),
                    )
                    result.abstracts.append(abstract_record)

                # Add URLs
                for url in data.get("urls", []):
                    from compute_forecast.pipeline.consolidation.models import (
                        URLRecord,
                        URLData,
                    )

                    url_record = URLRecord(
                        source="semantic_scholar",
                        timestamp=datetime.now(),
                        original=False,
                        data=URLData(url=url),
                    )
                    result.urls.append(url_record)

                # Add identifiers
                for identifier in data.get("identifiers", []):
                    from compute_forecast.pipeline.consolidation.models import (
                        IdentifierRecord,
                        IdentifierData,
                    )

                    identifier_record = IdentifierRecord(
                        source="semantic_scholar",
                        timestamp=datetime.now(),
                        original=False,
                        data=IdentifierData(
                            identifier_type=identifier["type"],
                            identifier_value=identifier["value"],
                        ),
                    )
                    result.identifiers.append(identifier_record)

                # Merge enrichment with paper using checkpoint manager's method
                from compute_forecast.pipeline.consolidation.checkpoint_manager import (
                    ConsolidationCheckpointManager,
                )

                checkpoint_manager = ConsolidationCheckpointManager()
                checkpoint_manager.merge_enrichments(paper, result)

                # Update statistics
                stats["papers_enriched"] += 1
                stats["citations_added"] += len(result.citations)
                stats["abstracts_added"] += len(result.abstracts)
                stats["urls_added"] += len(result.urls)
                stats["identifiers_added"] += len(result.identifiers)

                if progress_callback:
                    progress_callback(1)

        except Exception as e:
            logger.error(f"Error enriching batch from Semantic Scholar: {e}")

        # Mark all papers in this batch as processed
        batch_paper_ids = set()
        for ext_id in batch:
            if ext_id in id_to_paper:
                batch_paper_ids.add(id_to_paper[ext_id])

        for paper_id in batch_paper_ids:
            if paper_id in papers_by_id:
                paper = papers_by_id[paper_id]
                processed_hashes.add(get_paper_hash(paper))

        # Checkpoint after batch if callback provided
        if checkpoint_callback:
            checkpoint_callback(processed_hashes)

    # Mark any remaining papers without external IDs as processed
    for paper in papers_to_process:
        processed_hashes.add(get_paper_hash(paper))

    return stats


def main(
    input: Path = typer.Option(
        ..., "--input", "-i", help="Input JSON file from collect"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file path"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done"),
    no_progress: bool = typer.Option(
        False, "--no-progress", help="Disable progress bars"
    ),
    ss_api_key: Optional[str] = typer.Option(
        None,
        "--ss-api-key",
        help="Semantic Scholar API key",
        envvar="SEMANTIC_SCHOLAR_API_KEY",
    ),
    openalex_email: Optional[str] = typer.Option(
        None, "--openalex-email", help="OpenAlex email", envvar="OPENALEX_EMAIL"
    ),
    profile: bool = typer.Option(
        False, "--profile", help="Enable performance profiling"
    ),
    resume: bool = typer.Option(
        False, "--resume", help="Resume from previous checkpoint if available"
    ),
    checkpoint_interval: float = typer.Option(
        5.0, "--checkpoint-interval", help="Minutes between checkpoints (0 to disable)"
    ),
    phase1_batch_size: int = typer.Option(
        1, "--phase1-batch-size", help="Batch size for Phase 1 (OpenAlex ID harvesting)"
    ),
    phase2_batch_size: int = typer.Option(
        500,
        "--phase2-batch-size",
        help="Batch size for Phase 2 (Semantic Scholar enrichment)",
    ),
    phase3_batch_size: int = typer.Option(
        50, "--phase3-batch-size", help="Batch size for Phase 3 (OpenAlex enrichment)"
    ),
    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Increase verbosity level (-v for INFO, -vv for DEBUG)",
    ),
):
    """
    Two-phase consolidation and enrichment of paper metadata.

    This command uses an optimized two-phase approach:
    1. OpenAlex ID harvesting - Discovers DOIs, ArXiv IDs, and other identifiers
    2. Semantic Scholar batch enrichment - Uses discovered IDs for efficient lookups
    3. OpenAlex full enrichment - Comprehensive data including affiliations

    Examples:
        cf consolidate --input papers.json --output enriched.json
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
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[],  # Clear default handlers
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
        session_id = ConsolidationCheckpointManager.get_latest_resumable_session(
            str(input)
        )
        if not session_id:
            console.print(f"[yellow]No resumable session found for {input}[/yellow]")
            resume = False

    checkpoint_manager = ConsolidationCheckpointManager(
        session_id=session_id, checkpoint_interval_minutes=checkpoint_interval
    )

    # Initialize phase state
    phase_state = ConsolidationPhaseState(phase="id_harvesting")

    # Check for resume
    checkpoint_data = None
    papers = None

    if resume:
        checkpoint_result = checkpoint_manager.load_checkpoint()
        if checkpoint_result:
            checkpoint_data, papers = checkpoint_result
            console.print(
                f"[green]Resuming from checkpoint: {checkpoint_data.session_id}[/green]"
            )
            console.print(f"  Papers loaded: {len(papers)}")

            # Restore phase state if available
            if hasattr(checkpoint_data, "phase_state") and checkpoint_data.phase_state:
                phase_state = ConsolidationPhaseState.from_dict(
                    checkpoint_data.phase_state
                )
                console.print(f"  Current phase: {phase_state.phase}")
                console.print(f"  Phase completed: {phase_state.phase_completed}")
                console.print(
                    f"  Papers with external IDs: {phase_state.papers_with_external_ids}"
                )
                if phase_state.batch_progress:
                    console.print(f"  Batch progress: {phase_state.batch_progress}")
        else:
            console.print(
                "[yellow]No valid checkpoint found, starting from beginning[/yellow]"
            )

    # Load papers if not resuming
    if papers is None:
        console.print(f"[cyan]Loading papers from {input}...[/cyan]")
        with profile_operation("load_papers", file=str(input)):
            papers = load_papers(input)
        console.print(f"[green]Loaded {len(papers)} papers[/green]")

    if dry_run:
        console.print("\n[yellow]DRY RUN - Two-phase consolidation:[/yellow]")
        console.print("  Phase 1: OpenAlex ID harvesting")
        console.print("  Phase 2: Semantic Scholar enrichment (using discovered IDs)")
        console.print("  Phase 3: OpenAlex full enrichment")
        console.print(f"  Papers: {len(papers)}")
        return

    # Initialize sources
    openalex_config = SourceConfig(
        api_key=openalex_email,
        batch_size=phase3_batch_size,  # Default batch size for enrich_papers
        find_batch_size=phase1_batch_size,  # Batch size for finding papers in Phase 1
    )
    openalex_source = OpenAlexSource(openalex_config)

    ss_config = SourceConfig(api_key=ss_api_key)
    semantic_scholar_source = SemanticScholarSource(ss_config)

    # Track statistics
    stats = {
        "total_papers": len(papers),
        "phase1_identifiers_found": 0,
        "phase2_papers_enriched": 0,
        "phase3_papers_enriched": 0,
        "citations_added": 0,
        "abstracts_added": 0,
        "urls_added": 0,
        "identifiers_added": 0,
        "api_calls": {},
    }

    # Create progress display
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DetailedProgressColumn(),
        console=console,
        disable=no_progress,
    )

    with Live(
        progress,
        console=console,
        refresh_per_second=4,
        vertical_overflow="visible",
        transient=True,
    ) as live:
        # Add custom logging handler
        rich_handler = RichConsoleHandler(console, live)
        rich_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logging.getLogger().addHandler(rich_handler)

        # Phase 1: OpenAlex ID Harvesting (if not completed)
        if not phase_state.phase_completed or phase_state.phase == "id_harvesting":
            console.print("\n[bold cyan]Phase 1: OpenAlex ID Harvesting[/bold cyan]")
            phase_state.phase = "id_harvesting"
            phase_state.phase_start_time = datetime.now()

            # Create a separate progress bar for Phase 1 with custom column
            phase1_column = Phase1ProgressColumn()

            # If resuming, set existing identifiers
            if phase_state.identifiers_collected:
                phase1_column.set_identifiers(phase_state.identifiers_collected)

            phase1_progress_display = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                phase1_column,
                console=console,
                disable=no_progress,
            )

            # Replace the main progress with phase1 progress
            live.update(phase1_progress_display)

            phase1_task = phase1_progress_display.add_task(
                "[cyan]Harvesting identifiers[/cyan]", total=len(papers)
            )

            def phase1_progress(count):
                phase1_progress_display.advance(phase1_task, count)

            # Wrap source with logging
            logged_openalex = LoggingSourceWrapper(openalex_source)

            # Create checkpoint callback for Phase 1 that will receive identifiers and hashes
            def phase1_checkpoint(current_identifiers, current_hashes):
                # Update the progress column with current identifiers
                phase1_column.set_identifiers(current_identifiers)

                # Only checkpoint if enough time has passed
                if checkpoint_manager.should_checkpoint():
                    # Update phase state with current identifiers and hashes
                    phase_state.identifiers_collected = current_identifiers
                    phase_state.processed_paper_hashes = current_hashes
                    checkpoint_manager.save_checkpoint(
                        input_file=str(input),
                        total_papers=len(papers),
                        sources_state={"phase": "id_harvesting"},
                        papers=papers,
                        phase_state=phase_state.to_dict(),
                    )

            # Harvest identifiers
            start_time = time.time()
            identifiers = harvest_identifiers_openalex(
                papers,
                logged_openalex,
                phase1_progress,
                phase1_checkpoint,
                phase_state.identifiers_collected,  # Pass existing identifiers for resume
                phase_state.processed_paper_hashes,  # Pass processed hashes for resume
                batch_size=phase1_batch_size,
            )
            phase1_time = time.time() - start_time

            # Update phase state with final identifiers
            phase_state.identifiers_collected = identifiers
            phase_state.phase_completed = True
            phase_state.phase_end_time = datetime.now()

            # Ensure all processed papers are in the hash set
            for paper in papers:
                if paper.paper_id in identifiers:
                    phase_state.processed_paper_hashes.add(get_paper_hash(paper))

            # Count statistics
            for paper_ids in identifiers.values():
                if paper_ids.doi:
                    phase_state.papers_with_dois += 1
                if paper_ids.arxiv_id:
                    phase_state.papers_with_arxiv += 1
                if paper_ids.has_external_ids():
                    phase_state.papers_with_external_ids += 1

            stats["phase1_identifiers_found"] = len(identifiers)
            stats["api_calls"]["openalex_phase1"] = logged_openalex.api_calls

            phase1_progress_display.update(
                phase1_task, completed=len(papers)
            )  # Ensure it shows 100%

            # Restore main progress display
            live.update(progress)

            console.print("\n[green]Phase 1 Complete:[/green]")
            console.print(f"  Time: {phase1_time:.1f}s")
            console.print(
                f"  Papers found in OpenAlex: {len(identifiers)}/{len(papers)} ({len(identifiers) / len(papers) * 100:.1f}%)"
            )
            console.print(f"  Papers with DOIs: {phase_state.papers_with_dois}")
            console.print(f"  Papers with ArXiv IDs: {phase_state.papers_with_arxiv}")
            console.print(
                f"  Papers with external IDs: {phase_state.papers_with_external_ids}"
            )

            # Save checkpoint
            checkpoint_manager.save_checkpoint(
                input_file=str(input),
                total_papers=len(papers),
                sources_state={"phase": "id_harvesting_complete"},
                papers=papers,
                phase_state=phase_state.to_dict(),
                force=True,
            )

            # Enrich papers with discovered identifiers
            papers = enrich_papers_with_identifiers(papers, identifiers)

        # Phase 2: Semantic Scholar Enrichment (using discovered IDs)
        if phase_state.phase_completed and (
            phase_state.phase == "id_harvesting"
            or phase_state.phase == "semantic_scholar_enrichment"
        ):
            console.print(
                "\n[bold cyan]Phase 2: Semantic Scholar Enrichment[/bold cyan]"
            )
            phase_state.phase = "semantic_scholar_enrichment"
            phase_state.phase_start_time = datetime.now()
            phase_state.phase_completed = False

            # Filter papers that have external IDs for efficient S2 lookup
            papers_with_ids = []
            papers_without_ids = []

            for paper in papers:
                paper_ids = phase_state.identifiers_collected.get(paper.paper_id)
                if paper_ids and paper_ids.has_external_ids():
                    papers_with_ids.append(paper)
                else:
                    papers_without_ids.append(paper)

            console.print(f"  Papers with external IDs: {len(papers_with_ids)}")
            console.print(f"  Papers without external IDs: {len(papers_without_ids)}")

            if papers_with_ids:
                phase2_task = progress.add_task(
                    f"[cyan]Semantic Scholar enrichment ({len(papers_with_ids)} papers with IDs)[/cyan]",
                    total=len(papers_with_ids),
                )

                def phase2_progress(count):
                    progress.advance(phase2_task, count)

                # Create checkpoint callback for Phase 2
                def phase2_checkpoint(current_hashes):
                    # Only checkpoint if enough time has passed
                    if checkpoint_manager.should_checkpoint():
                        phase_state.processed_paper_hashes = current_hashes
                        checkpoint_manager.save_checkpoint(
                            input_file=str(input),
                            total_papers=len(papers),
                            sources_state={"phase": "semantic_scholar_enrichment"},
                            papers=papers,
                            phase_state=phase_state.to_dict(),
                        )

                # Wrap source with logging
                logged_ss = LoggingSourceWrapper(semantic_scholar_source)

                # Perform batch enrichment
                start_time = time.time()
                phase2_stats = enrich_semantic_scholar_batch(
                    papers_with_ids,
                    phase_state.identifiers_collected,
                    logged_ss,
                    phase2_progress,
                    phase2_checkpoint,
                    phase_state.batch_progress,
                    phase_state.processed_paper_hashes,
                    batch_size=phase2_batch_size,
                )
                phase2_time = time.time() - start_time

                stats["phase2_papers_enriched"] = phase2_stats["papers_enriched"]
                stats["citations_added"] += phase2_stats["citations_added"]
                stats["abstracts_added"] += phase2_stats["abstracts_added"]
                stats["urls_added"] += phase2_stats["urls_added"]
                stats["identifiers_added"] += phase2_stats["identifiers_added"]
                stats["api_calls"]["semantic_scholar"] = logged_ss.api_calls

                progress.update(
                    phase2_task, completed=len(papers_with_ids)
                )  # Ensure it shows 100%

                console.print("\n[green]Phase 2 Complete:[/green]")
                console.print(f"  Time: {phase2_time:.1f}s")
                console.print(f"  Papers enriched: {phase2_stats['papers_enriched']}")
                console.print(f"  Citations added: {phase2_stats['citations_added']}")
                console.print(f"  Abstracts added: {phase2_stats['abstracts_added']}")
                console.print(f"  URLs added: {phase2_stats['urls_added']}")
                console.print(
                    f"  Identifiers added: {phase2_stats['identifiers_added']}"
                )
                console.print(f"  API calls: {logged_ss.api_calls}")

                # Ensure all papers from Phase 2 are marked as processed
                for paper in papers_with_ids:
                    phase_state.processed_paper_hashes.add(get_paper_hash(paper))

            # Mark papers without IDs as processed too (they won't be retried)
            for paper in papers_without_ids:
                phase_state.processed_paper_hashes.add(get_paper_hash(paper))

            phase_state.phase_completed = True
            phase_state.phase_end_time = datetime.now()

            # Save checkpoint
            checkpoint_manager.save_checkpoint(
                input_file=str(input),
                total_papers=len(papers),
                sources_state={"phase": "semantic_scholar_complete"},
                papers=papers,
                phase_state=phase_state.to_dict(),
                force=True,
            )

        # Phase 3: OpenAlex Full Enrichment
        if phase_state.phase_completed and (
            phase_state.phase == "semantic_scholar_enrichment"
            or phase_state.phase == "openalex_enrichment"
        ):
            console.print("\n[bold cyan]Phase 3: OpenAlex Full Enrichment[/bold cyan]")
            phase_state.phase = "openalex_enrichment"
            phase_state.phase_start_time = datetime.now()
            phase_state.phase_completed = False

            # Use all papers for OpenAlex enrichment
            phase3_task = progress.add_task(
                f"[cyan]OpenAlex full enrichment ({len(papers)} papers)[/cyan]",
                total=len(papers),
            )

            def phase3_progress(result):
                progress.advance(phase3_task, 1)

            # Wrap source with logging
            logged_oa = LoggingSourceWrapper(openalex_source)

            # Perform full enrichment using the standard enrich_papers method
            start_time = time.time()

            # Track statistics
            phase3_citations = 0
            phase3_abstracts = 0
            phase3_urls = 0
            phase3_identifiers = 0
            phase3_enriched = 0

            # Use the source's enrich_papers method which handles batching internally
            enrichment_results = logged_oa.enrich_papers(
                papers, progress_callback=phase3_progress
            )

            # Apply enrichments and track statistics
            for result in enrichment_results:
                if result.paper_id in {p.paper_id for p in papers}:
                    # Find the paper
                    paper = next(p for p in papers if p.paper_id == result.paper_id)

                    # Merge enrichments
                    checkpoint_manager.merge_enrichments(paper, result)

                    # Track statistics
                    if result.citations:
                        phase3_citations += len(result.citations)
                    if result.abstracts:
                        phase3_abstracts += len(result.abstracts)
                    if result.urls:
                        phase3_urls += len(result.urls)
                    if result.identifiers:
                        phase3_identifiers += len(result.identifiers)

                    if any(
                        [
                            result.citations,
                            result.abstracts,
                            result.urls,
                            result.identifiers,
                        ]
                    ):
                        phase3_enriched += 1

            phase3_time = time.time() - start_time

            stats["phase3_papers_enriched"] = phase3_enriched
            stats["citations_added"] += phase3_citations
            stats["abstracts_added"] += phase3_abstracts
            stats["urls_added"] += phase3_urls
            stats["identifiers_added"] += phase3_identifiers
            stats["api_calls"]["openalex_phase3"] = logged_oa.api_calls

            progress.update(phase3_task, completed=len(papers))  # Ensure it shows 100%

            console.print("\n[green]Phase 3 Complete:[/green]")
            console.print(f"  Time: {phase3_time:.1f}s")
            console.print(f"  Papers enriched: {phase3_enriched}")
            console.print(f"  Citations added: {phase3_citations}")
            console.print(f"  Abstracts added: {phase3_abstracts}")
            console.print(f"  URLs added: {phase3_urls}")
            console.print(f"  Identifiers added: {phase3_identifiers}")
            console.print(f"  API calls: {logged_oa.api_calls}")

            # Mark all papers as processed in Phase 3
            for paper in papers:
                phase_state.processed_paper_hashes.add(get_paper_hash(paper))

            phase_state.phase_completed = True
            phase_state.phase_end_time = datetime.now()
            phase_state.phase = "completed"

            # Save final checkpoint
            checkpoint_manager.save_checkpoint(
                input_file=str(input),
                total_papers=len(papers),
                sources_state={"phase": "completed"},
                papers=papers,
                phase_state=phase_state.to_dict(),
                force=True,
            )

    # Save results
    output.parent.mkdir(parents=True, exist_ok=True)
    with profile_operation("save_papers", file=str(output)):
        save_papers(papers, output, stats)

    console.print(f"\n[green]✓[/green] Saved enriched data to {output}")
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Total papers: {stats['total_papers']}")
    console.print(f"  Phase 1 identifiers found: {stats['phase1_identifiers_found']}")
    console.print(f"  Phase 2 papers enriched: {stats['phase2_papers_enriched']}")
    console.print(f"  Phase 3 papers enriched: {stats['phase3_papers_enriched']}")
    console.print(f"  Total citations added: {stats['citations_added']}")
    console.print(f"  Total abstracts added: {stats['abstracts_added']}")
    console.print(f"  Total URLs added: {stats['urls_added']}")
    console.print(f"  Total identifiers added: {stats['identifiers_added']}")
    console.print(f"  Total API calls: {sum(stats['api_calls'].values())}")
    for source, calls in stats["api_calls"].items():
        console.print(f"    {source}: {calls}")

    # Clean up checkpoint files after successful completion
    checkpoint_manager.cleanup()

    # Print profiling report if enabled
    if profile:
        profiler.print_report()

        # Also save detailed breakdown
        breakdown = profiler.get_detailed_breakdown()
        profile_path = output.parent / f"profile_{output.stem}.json"
        with open(profile_path, "w") as f:
            json.dump(
                {
                    "summary": profiler.get_summary(),
                    "breakdown": breakdown,
                    "records": [
                        {"name": r.name, "duration": r.duration, "metadata": r.metadata}
                        for r in profiler.records
                        if r.duration
                    ],
                },
                f,
                indent=2,
            )
        console.print(f"\n[dim]Detailed profile saved to {profile_path}[/dim]")
