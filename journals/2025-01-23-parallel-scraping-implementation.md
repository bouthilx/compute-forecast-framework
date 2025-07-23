# 2025-01-23 - Parallel Scraping Implementation Plan

## Overview

The current collection system processes venues and years sequentially, leading to very slow collection times. We need to implement a parallel collection system with:
- One worker process per venue
- Real-time progress bars for each (venue, year) combination
- Paper-by-paper streaming from scrapers to main process via queues

## Architecture Design

### Core Components

1. **Main Process (Orchestrator)**
   - Creates and manages worker processes (one per venue)
   - Maintains progress bars using Rich Live display
   - Collects papers from shared queue
   - Handles checkpointing and final output

2. **Worker Processes**
   - One worker per venue, processing years sequentially
   - Streams papers one-by-one to shared queue
   - Handles scraper initialization and error recovery

3. **Queue-Based Communication**
   ```python
   @dataclass
   class CollectionResult:
       venue: str
       year: int
       paper: Optional[SimplePaper] = None
       error: Optional[str] = None
       is_complete: bool = False  # Signals end of venue/year
       total_expected: Optional[int] = None  # For progress bar initialization
   ```

### Implementation Details

#### Main Process Flow
```python
def collect_parallel(venues: Dict[str, List[int]], config: ScrapingConfig):
    # 1. Create shared queue and worker processes
    result_queue = multiprocessing.Queue()
    workers = []
    
    # 2. Initialize progress tracking
    progress_tasks = {}  # (venue, year) -> task_id
    progress = Progress(...)
    
    # 3. Start workers
    for venue, years in venues.items():
        worker = VenueWorker(venue, years, config, result_queue)
        worker.start()
        workers.append(worker)
    
    # 4. Create progress bars for all venue/year combinations
    for venue, years in venues.items():
        for year in sorted(years):
            task = progress.add_task(f"{venue} {year}", total=None)
            progress_tasks[(venue, year)] = task
    
    # 5. Process results from queue
    with Live(progress, ...):
        all_papers = []
        active_workers = len(workers)
        
        while active_workers > 0:
            try:
                result = result_queue.get(timeout=0.1)
                
                if result.is_complete:
                    if result.venue == "WORKER_DONE":
                        active_workers -= 1
                    continue
                
                # Update progress bar
                task_id = progress_tasks[(result.venue, result.year)]
                
                if result.total_expected and progress.tasks[task_id].total is None:
                    # Initialize total for progress bar
                    progress.update(task_id, total=result.total_expected)
                
                if result.paper:
                    all_papers.append(result.paper)
                    progress.advance(task_id, 1)
                elif result.error:
                    logger.error(f"Error collecting {result.venue} {result.year}: {result.error}")
                    
            except queue.Empty:
                continue
```

#### Worker Process Implementation
```python
class VenueWorker(multiprocessing.Process):
    def __init__(self, venue: str, years: List[int], config: ScrapingConfig, result_queue: Queue):
        super().__init__()
        self.venue = venue
        self.years = sorted(years)
        self.config = config
        self.result_queue = result_queue
        
    def run(self):
        # Get appropriate scraper
        registry = get_registry()
        scraper = registry.get_scraper_for_venue(self.venue, self.config)
        
        for year in self.years:
            try:
                # First, estimate paper count
                estimated_count = scraper.estimate_paper_count(self.venue, year)
                if estimated_count:
                    self.result_queue.put(CollectionResult(
                        venue=self.venue,
                        year=year,
                        total_expected=estimated_count
                    ))
                
                # Stream papers one by one
                for paper in scraper.scrape_venue_year_iter(self.venue, year):
                    self.result_queue.put(CollectionResult(
                        venue=self.venue,
                        year=year,
                        paper=paper
                    ))
                
                # Signal completion of venue/year
                self.result_queue.put(CollectionResult(
                    venue=self.venue,
                    year=year,
                    is_complete=True
                ))
                
            except Exception as e:
                self.result_queue.put(CollectionResult(
                    venue=self.venue,
                    year=year,
                    error=str(e)
                ))
        
        # Signal worker completion
        self.result_queue.put(CollectionResult(
            venue="WORKER_DONE",
            year=0,
            is_complete=True
        ))
```

### Progress Bar Layout

Using Rich's Live display with fixed progress bars at bottom:
- Logs scroll above the progress bars
- Progress bars ordered by: venue order (as passed), then year
- Format: `venue year ━━━━━━━━━━━━━━━ percentage%, (done/total) elapsed (ETA)`

## Scraper Conversion Plan

### General Approach

All scrapers need a new method `scrape_venue_year_iter()` that yields papers one by one. The existing `scrape_venue_year()` method can be reimplemented to use the iterator internally for backwards compatibility.

### Base Class Changes

```python
# In BaseScraper
def scrape_venue_year_iter(self, venue: str, year: int) -> Iterator[SimplePaper]:
    """Iterator version of scrape_venue_year. Override in subclasses."""
    # Default implementation for backwards compatibility
    result = self.scrape_venue_year(venue, year)
    if result.success and result.metadata.get("papers"):
        yield from result.metadata["papers"]

def scrape_venue_year(self, venue: str, year: int) -> ScrapingResult:
    """Collect all papers. Can be reimplemented using scrape_venue_year_iter."""
    papers = list(self.scrape_venue_year_iter(venue, year))
    # ... create ScrapingResult
```

### 1. OpenReviewScraperV2 Conversion

Current structure:
- `scrape_venue_year()` calls `_fetch_all_papers()`
- `_fetch_all_papers()` fetches all papers then filters/processes in bulk

Changes needed:
```python
def scrape_venue_year_iter(self, venue: str, year: int) -> Iterator[SimplePaper]:
    """Stream papers one by one as they are fetched and processed."""
    venue_id = self._get_venue_id(venue, year)
    if not venue_id:
        return
    
    offset = 0
    while True:
        # Fetch batch from API
        url = f"{self.base_url}/notes"
        params = {
            "invitation": f"{venue_id}/-/Blind_Submission",
            "details": "invitation,original",
            "offset": offset,
            "limit": self.batch_size,
        }
        
        response = self._make_request(url, params=params)
        data = response.json()
        notes = data.get("notes", [])
        
        if not notes:
            break
            
        # Process and yield papers one by one
        for note in notes:
            if self._is_accepted_paper(note):
                paper = self._extract_paper_info(note, venue, year)
                if paper:
                    yield paper
        
        offset += len(notes)
        if len(notes) < self.batch_size:
            break
```

### 2. NeurIPSScraper Conversion

Current structure:
- `_call_paperoni_scraper()` fetches all paper entries from proceedings page
- Processes all papers in a loop, collecting them in a list

Changes needed:
```python
def scrape_venue_year_iter(self, venue: str, year: int) -> Iterator[SimplePaper]:
    """Stream NeurIPS papers one by one."""
    try:
        # Fetch the proceedings page
        url = f"{self.base_url}/paper_files/paper/{year}"
        response = self._make_request(url)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find all paper entries
        paper_entries = []
        for li in soup.find_all("li"):
            link = li.find("a", href=lambda x: x and "hash" in x)
            if link:
                paper_entries.append(li)
        
        self.logger.info(f"Found {len(paper_entries)} paper entries on NeurIPS {year} page")
        
        # Process and yield papers one by one
        for i, entry in enumerate(paper_entries):
            try:
                # Extract paper info
                link_elem = entry.find("a")
                if not link_elem or "hash" not in link_elem.get("href", ""):
                    continue
                
                paper_url = link_elem["href"]
                if not paper_url.startswith("http"):
                    paper_url = self.base_url + paper_url
                
                title = link_elem.text.strip()
                
                # Extract authors
                authors_elem = entry.find("i")
                authors = []
                if authors_elem:
                    authors_text = authors_elem.text
                    authors = [a.strip() for a in authors_text.split(",")]
                
                # Extract hash and get PDF URL
                hash_match = re.search(r"hash/([^-]+)", paper_url)
                if hash_match:
                    paper_hash = hash_match.group(1)
                    pdf_url = self._fetch_pdf_url_from_page(paper_url, paper_hash)
                    
                    if not pdf_url:
                        # Fallback to pattern-based URL
                        year_int = int(year)
                        if year_int >= 2022:
                            pdf_url = f"{self.base_url}/paper_files/paper/{year}/file/{paper_hash}-Paper-Conference.pdf"
                        else:
                            pdf_url = f"{self.base_url}/paper_files/paper/{year}/file/{paper_hash}-Paper.pdf"
                
                # Create and yield SimplePaper
                paper = SimplePaper(
                    title=title,
                    authors=authors,
                    venue="NeurIPS",
                    year=year,
                    pdf_urls=[pdf_url],
                    source_scraper=self.source_name,
                    source_url=paper_url,
                    scraped_at=datetime.now(),
                    extraction_confidence=0.9,
                )
                
                yield paper
                
            except Exception as e:
                self.logger.warning(f"Failed to parse paper entry {i+1}: {e}")
                continue
                
    except Exception as e:
        self.logger.error(f"Failed to fetch NeurIPS {year} proceedings: {e}")
        return
```

### 3. PMLRScraper Conversion

Current structure:
- `scrape_venue_year()` fetches proceedings page
- Extracts all paper info at once

Changes needed:
```python
def scrape_venue_year_iter(self, venue: str, year: int) -> Iterator[SimplePaper]:
    """Stream PMLR papers one by one."""
    volume = self._get_volume_for_venue_year(venue, year)
    if not volume:
        return
    
    url = f"{self.base_url}/v{volume}/"
    try:
        response = self._make_request(url)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find all paper entries
        paper_entries = soup.find_all("div", class_="paper")
        
        for entry in paper_entries:
            try:
                # Extract title
                title_elem = entry.find("p", class_="title")
                if not title_elem:
                    continue
                title = title_elem.text.strip()
                
                # Extract authors
                authors_elem = entry.find("p", class_="details")
                authors = []
                if authors_elem:
                    authors_text = authors_elem.find("span", class_="authors")
                    if authors_text:
                        authors = [a.strip() for a in authors_text.text.split(",")]
                
                # Extract PDF URL
                links = entry.find_all("a")
                pdf_url = None
                for link in links:
                    if "pdf" in link.text.lower():
                        pdf_url = urljoin(url, link["href"])
                        break
                
                if not pdf_url:
                    continue
                
                # Create and yield paper
                paper = SimplePaper(
                    title=title,
                    authors=authors,
                    venue=venue.upper(),
                    year=year,
                    pdf_urls=[pdf_url],
                    source_scraper=self.source_name,
                    source_url=url,
                    scraped_at=datetime.now(),
                    extraction_confidence=0.95,
                )
                
                yield paper
                
            except Exception as e:
                self.logger.warning(f"Failed to parse PMLR paper entry: {e}")
                continue
                
    except Exception as e:
        self.logger.error(f"Failed to fetch PMLR volume {volume}: {e}")
        return
```

## Implementation Priority

1. **Phase 1**: Implement scraper conversion for the three scrapers
   - Add `scrape_venue_year_iter()` methods
   - Test streaming functionality
   - Ensure backwards compatibility

2. **Phase 2**: Implement parallel collection infrastructure
   - Create worker process class
   - Implement queue-based communication
   - Add progress bar management

3. **Phase 3**: Integration and testing
   - Update collect command to use parallel mode
   - Add proper error handling and recovery
   - Test with multiple venues/years

## Benefits

1. **Performance**: Parallel processing of venues dramatically reduces total collection time
2. **User Experience**: Real-time progress updates per venue/year
3. **Memory Efficiency**: Streaming papers instead of loading all at once
4. **Flexibility**: Can easily add more sophisticated scheduling (e.g., dynamic worker allocation)

## Risks and Mitigations

1. **Rate Limiting**: Workers might hit rate limits faster
   - Mitigation: Keep per-worker rate limits, possibly make them configurable per venue

2. **Memory Usage**: Queue might grow if producer faster than consumer
   - Mitigation: Use bounded queue with backpressure

3. **Error Recovery**: Worker crashes need proper handling
   - Mitigation: Implement worker restart logic and checkpoint recovery

4. **Scraper Compatibility**: Not all scrapers may be easily convertible
   - Mitigation: Keep fallback to non-streaming mode for incompatible scrapers