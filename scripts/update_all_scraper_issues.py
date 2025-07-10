#!/usr/bin/env python3
"""Update all scraper milestone issues with complete descriptions from journal"""

import subprocess

# Read the complete journal content
with open("journals/complete_scraper_milestone.md", "r") as f:
    journal_content = f.read()

# Split the content into sections for each issue
issues = {}
current_issue = None
current_content = []

for line in journal_content.split("\n"):
    if line.startswith("### Issue #"):
        # Save previous issue if exists
        if current_issue:
            issues[current_issue] = "\n".join(current_content)

        # Start new issue
        try:
            issue_num = int(line.split(":")[0].replace("### Issue #", ""))
            current_issue = issue_num
            current_content = []
        except Exception:
            pass
    elif current_issue:
        current_content.append(line)

# Save last issue
if current_issue:
    issues[current_issue] = "\n".join(current_content)

# Map GitHub issue numbers to journal issue numbers
# Journal has issues 1-16, GitHub has issues 140-155
issue_mapping = {
    1: 140,  # Base Scraper Classes
    2: 141,  # Enhanced Data Models
    3: 142,  # Institution Filtering Wrapper
    4: 143,  # Error Handling
    5: 144,  # IJCAI Scraper
    6: 145,  # ACL Anthology Scraper
    7: 146,  # CVF Scraper
    8: 147,  # Enhanced OpenReview
    9: 148,  # Enhanced PMLR
    10: 149,  # Nature Family
    11: 150,  # AAAI Scraper
    12: 151,  # Medical Journals
    13: 152,  # Unified Pipeline
    14: 153,  # Quality Validation
    15: 154,  # Performance Optimization
    16: 155,  # Documentation & Testing
}

# Special handling for Issue #2 (141) - use simplified approach
simplified_issue_2 = """**Priority**: Critical
**Estimate**: M (4-6 hours)
**Dependencies**: Issue #140 (Base Scraper Classes Framework)

#### Description
Create simple adapter models to bridge the gap between various scraper outputs (including paperoni) and the package's data structures.

#### Updated Approach (Simplified)

Based on analysis of paperoni's complex model structure, we'll use a simple adapter pattern instead of complex nested models.

#### Detailed Implementation

```python
# compute_forecast/data/sources/scrapers/models.py

from compute_forecast.data.models import Paper, Author
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class SimplePaper:
    \"\"\"Minimal paper representation from any scraper\"\"\"
    # Core fields
    title: str
    authors: List[str]  # Simple list of author names
    venue: str
    year: int

    # Optional fields
    abstract: Optional[str] = None
    pdf_url: Optional[str] = None
    doi: Optional[str] = None

    # Source tracking
    source_scraper: str = ""
    source_url: str = ""
    scraped_at: datetime = field(default_factory=datetime.now)

    # Quality indicators
    extraction_confidence: float = 1.0

    def to_package_paper(self) -> Paper:
        \"\"\"Convert to package's Paper model\"\"\"
        return Paper(
            title=self.title,
            authors=[Author(name=name, affiliation="") for name in self.authors],
            venue=self.venue,
            year=self.year,
            abstract=self.abstract or "",
            doi=self.doi or "",
            urls=[self.pdf_url] if self.pdf_url else [],
            collection_source=self.source_scraper,
            collection_timestamp=self.scraped_at
        )

class PaperoniAdapter:
    \"\"\"Adapter to convert paperoni models to SimplePaper\"\"\"

    @staticmethod
    def convert(paperoni_paper) -> SimplePaper:
        \"\"\"Convert a paperoni Paper object to SimplePaper\"\"\"
        # Extract basic fields
        title = paperoni_paper.title

        # Extract authors (paperoni has complex PaperAuthor → Author structure)
        authors = []
        for paper_author in paperoni_paper.authors:
            if hasattr(paper_author, 'author') and hasattr(paper_author.author, 'name'):
                authors.append(paper_author.author.name)

        # Extract venue and year from releases
        venue = ""
        year = None
        if paperoni_paper.releases:
            release = paperoni_paper.releases[0]
            if hasattr(release, 'venue') and hasattr(release.venue, 'name'):
                venue = release.venue.name
            if hasattr(release, 'date'):
                year = release.date.year

        # Extract PDF URL from links
        pdf_url = None
        for link in paperoni_paper.links:
            if hasattr(link, 'type') and 'pdf' in str(link.type).lower():
                pdf_url = link.url
                break

        return SimplePaper(
            title=title,
            authors=authors,
            venue=venue,
            year=year or datetime.now().year,
            abstract=paperoni_paper.abstract,
            pdf_url=pdf_url,
            doi=getattr(paperoni_paper, 'doi', None),
            source_scraper="paperoni",
            extraction_confidence=0.95  # High confidence for established scrapers
        )

@dataclass
class ScrapingBatch:
    \"\"\"Container for a batch of scraped papers\"\"\"
    papers: List[SimplePaper]
    source: str
    venue: str
    year: int
    total_found: int
    successfully_parsed: int
    errors: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.successfully_parsed / max(1, self.total_found)
```

#### Usage Examples

```python
# For custom scrapers
papers = []
for entry in scraped_data:
    paper = SimplePaper(
        title=entry['title'],
        authors=entry['authors'],
        venue='IJCAI',
        year=2024,
        pdf_url=entry['pdf'],
        source_scraper='ijcai_scraper'
    )
    papers.append(paper)

# For paperoni scrapers
from paperoni.sources import NeurIPSScraper
neurips = NeurIPSScraper()
adapter = PaperoniAdapter()

papers = []
for paperoni_paper in neurips.query(year=2024):
    simple_paper = adapter.convert(paperoni_paper)
    papers.append(simple_paper)

# Convert to package format
package_papers = [p.to_package_paper() for p in papers]
```

#### Rationale for Simplified Approach

1. **Paperoni models are too complex**: Deeply nested with quality tuples, merge tracking, etc.
2. **We only need core fields**: Title, authors, venue, year, PDF URL
3. **Adapter pattern is cleaner**: Convert at the boundary, work with simple data internally
4. **Maintains compatibility**: Can work with both paperoni and custom scrapers

#### Acceptance Criteria
- [ ] SimplePaper model captures essential paper metadata
- [ ] PaperoniAdapter successfully converts paperoni models
- [ ] to_package_paper() method provides clean integration
- [ ] Extraction confidence tracking for quality filtering
- [ ] Minimal dependencies and complexity

#### Implementation Location
`compute_forecast/data/sources/scrapers/models.py`"""

# Update each issue
for journal_num, github_num in issue_mapping.items():
    print(f"Updating issue #{github_num} (journal issue #{journal_num})...")

    if journal_num == 2:  # Special case for simplified Issue #141
        body = simplified_issue_2
    else:
        body = issues.get(journal_num, "")

    if not body:
        print(f"  Warning: No content found for journal issue #{journal_num}")
        continue

    # Remove the leading "---" if present
    body = body.strip()
    if body.startswith("---"):
        body = body[3:].strip()

    # Add "## " before Priority if missing
    if not body.startswith("## Priority") and body.startswith("**Priority"):
        body = "## Priority\n" + body[11:]  # Remove "**Priority**:"

    # Escape the body content for shell
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(body)
        temp_file = f.name

    # Update the issue
    try:
        result = subprocess.run(
            ["gh", "issue", "edit", str(github_num), "--body-file", temp_file],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"  ✓ Successfully updated issue #{github_num}")
        else:
            print(f"  ✗ Failed to update issue #{github_num}: {result.stderr}")
    except Exception as e:
        print(f"  ✗ Error updating issue #{github_num}: {e}")
    finally:
        import os

        os.unlink(temp_file)

print("\nAll issues have been updated with complete descriptions from the journal.")
print("Issue #141 has been updated with the simplified adapter approach.")
