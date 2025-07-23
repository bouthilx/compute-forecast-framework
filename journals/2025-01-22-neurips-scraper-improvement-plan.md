# NeurIPS Scraper Improvement Plan

**Date**: 2025-01-22  
**Title**: Plan to Implement Dynamic PDF Discovery for NeurIPS Scraper

## Objective

Modify the NeurIPS scraper to dynamically discover PDF URLs from paper pages instead of inferring them from patterns, ensuring compatibility with all years and future-proofing against URL structure changes.

## Implementation Plan

### 1. Add PDF Discovery Method (New)

Create a new method `_fetch_pdf_url_from_page()` that:
- Takes the paper's HTML URL as input
- Fetches the paper page
- Extracts the correct PDF link from the page
- Returns the PDF URL or None if not found

```python
def _fetch_pdf_url_from_page(self, html_url: str, paper_hash: str) -> Optional[str]:
    """Fetch the actual PDF URL from the paper's HTML page."""
    # Implementation details below
```

### 2. Modify Main Scraping Logic

Update the `_call_paperoni_scraper()` method to:
1. Continue constructing the initial paper URL as before
2. Call `_fetch_pdf_url_from_page()` to get the actual PDF URL
3. Fall back to pattern-based URL if fetch fails
4. Validate the URL format and log warnings for unknown patterns

### 3. Add URL Pattern Validation

Create a method to validate known URL patterns:
- Check if the PDF URL matches one of the known patterns:
  - `-Paper.pdf` (2019-2021) - Main paper
  - `-Paper-Conference.pdf` (2022+) - Main paper
  - `-AuthorFeedback.pdf` (2019-2020) - Review/feedback, NOT the main paper
  - `-Supplemental.pdf` or `-Supplemental-Conference.pdf` - Supplemental materials only
- Ensure we select the main paper PDF, not supplemental or review materials
- Log a warning if an unknown pattern is detected
- Still use the URL even if pattern is unknown (but not for known non-paper patterns)

### 4. Error Handling

Implement robust error handling:
- Retry logic for failed page fetches (with exponential backoff)
- Fall back to pattern-based URL if page fetch fails
- Log all errors and warnings appropriately
- Continue processing even if individual papers fail

### 5. Performance Considerations

To minimize impact on scraping speed:
- Use connection pooling for HTTP requests
- Implement request caching if the same page is accessed multiple times
- Consider parallel fetching for multiple papers (if not already implemented)
- Add configurable delay between requests to be respectful to the server

## Detailed Implementation Steps

### Step 1: Update imports
```python
import time
from typing import Optional
from urllib.parse import urljoin
```

### Step 2: Add the PDF discovery method
```python
def _fetch_pdf_url_from_page(self, html_url: str, paper_hash: str) -> Optional[str]:
    """
    Fetch the actual PDF URL from the paper's HTML page.
    
    Args:
        html_url: The URL of the paper's HTML page
        paper_hash: The paper's hash identifier
        
    Returns:
        The PDF URL if found, None otherwise
    """
    try:
        # Fetch the paper page
        response = self._make_request(html_url)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Look for PDF links using button classes - much safer than searching all links
        main_paper_url = None
        other_pdfs = []
        
        # Strategy 1: For 2022+, look for btn-primary (exactly one per page, always the main paper)
        btn_primary = soup.find("a", class_="btn-primary")
        if btn_primary and btn_primary.get("href", "").endswith(".pdf"):
            href = btn_primary["href"]
            if paper_hash in href:
                main_paper_url = href
                self.logger.debug(f"Found main paper via btn-primary: {btn_primary.text.strip()}")
        
        # Strategy 2: If no btn-primary (2019-2021), look for button with text "Paper"
        if not main_paper_url:
            pdf_buttons = soup.find_all("a", class_="btn")
            
            for button in pdf_buttons:
                href = button.get("href", "")
                text = button.text.strip()
                
                # Check if this is a PDF link for this paper
                if paper_hash in href and href.endswith(".pdf"):
                    # Use text to identify the PDF type - most reliable method
                    if text == "Paper":
                        # This is the main paper
                        main_paper_url = href
                        self.logger.debug(f"Found main paper button via text: {text}")
                        break
                    elif text == "Supplemental":
                        other_pdfs.append((href, "supplemental"))
                    elif text == "AuthorFeedback":
                        other_pdfs.append((href, "feedback"))
                    else:
                        # Unknown button text
                        self.logger.warning(f"Unknown PDF button text: '{text}' for {href}")
                        other_pdfs.append((href, f"unknown-{text}"))
        
        # Use main paper if found, otherwise log what we skipped
        if main_paper_url:
            pdf_url = main_paper_url
            if not pdf_url.startswith("http"):
                pdf_url = urljoin(self.base_url, pdf_url)
            
            self.logger.debug(f"Selected main paper PDF: {pdf_url}")
        elif other_pdfs:
            self.logger.warning(
                f"No main paper PDF found for {paper_hash}. "
                f"Skipped PDFs: {[(url, type) for url, type in other_pdfs]}"
            )
            return None
        else:
            return None
        
        # Validate the URL pattern
        self._validate_pdf_url_pattern(pdf_url, html_url)
        
        return pdf_url
            
    except Exception as e:
        self.logger.warning(
            f"Failed to fetch PDF URL from page {html_url}: {e}"
        )
    
    return None
```

### Step 3: Add pattern validation
```python
def _validate_pdf_url_pattern(self, pdf_url: str, html_url: str) -> None:
    """
    Validate that the PDF URL matches a known pattern for main papers.
    Log a warning if an unknown pattern is detected.
    """
    main_paper_patterns = [
        "-Paper.pdf",
        "-Paper-Conference.pdf"
    ]
    
    non_paper_patterns = [
        "-AuthorFeedback.pdf",
        "-Supplemental.pdf",
        "-Supplemental-Conference.pdf"
    ]
    
    # Extract the suffix after the hash
    if "/file/" in pdf_url and "-" in pdf_url:
        suffix = pdf_url.split("/file/")[-1].split("-", 1)[-1]
        
        if suffix in main_paper_patterns:
            self.logger.debug(f"Confirmed main paper pattern: {suffix}")
        elif suffix in non_paper_patterns:
            self.logger.error(
                f"Non-paper PDF pattern detected but being used: {suffix} "
                f"This should not happen! (from HTML: {html_url})"
            )
        else:
            self.logger.warning(
                f"Unknown PDF URL pattern detected: {suffix} "
                f"(from HTML: {html_url})"
            )
```

### Step 4: Update main scraping logic
```python
# In _call_paperoni_scraper method, replace lines 102-110 with:

# Extract hash for PDF URL
hash_match = re.search(r"hash/([^-]+)", paper_url)
if hash_match:
    paper_hash = hash_match.group(1)
    
    # Try to fetch actual PDF URL from page
    pdf_url = self._fetch_pdf_url_from_page(paper_url, paper_hash)
    
    if not pdf_url:
        # Fall back to pattern-based URL (with year-aware logic)
        year_int = int(year)
        if year_int >= 2022:
            # Use Conference pattern for 2022+
            pdf_url = f"{self.base_url}/paper_files/paper/{year}/file/{paper_hash}-Paper-Conference.pdf"
        else:
            # Use standard pattern for 2021 and earlier
            pdf_url = f"{self.base_url}/paper_files/paper/{year}/file/{paper_hash}-Paper.pdf"
        
        self.logger.debug(
            f"Using pattern-based PDF URL for {paper_hash}: {pdf_url}"
        )
else:
    # Fallback for unexpected URL format
    pdf_url = paper_url.replace("/hash/", "/file/").replace(".html", ".pdf")
    self.logger.warning(f"Could not extract hash from URL: {paper_url}")
```

### Step 5: Add configuration for request delays
```python
# In __init__ method
self.request_delay = getattr(config, 'request_delay', 0.5)  # Default 0.5 seconds

# In _fetch_pdf_url_from_page method, after successful fetch:
if self.request_delay > 0:
    time.sleep(self.request_delay)
```

## Testing Plan

1. **Unit Tests**: Create tests for the new methods with mocked responses
2. **Integration Tests**: Test with real NeurIPS pages from different years
3. **Pattern Detection Tests**: Ensure warnings are logged for unknown patterns
4. **Error Handling Tests**: Test behavior when page fetch fails
5. **Performance Tests**: Measure impact of additional HTTP requests

## Rollback Plan

If issues arise, the implementation includes fallback logic to pattern-based URLs, so the scraper will continue to work (with the original limitations) even if the new dynamic discovery fails.

## Success Metrics

1. Successfully extract correct PDF URLs for all years (2019-2024)
2. Log warnings for any unknown URL patterns discovered
3. Maintain reasonable scraping performance (< 2x slower)
4. Handle errors gracefully without stopping the entire scraping process

## Timeline

- Implementation: 2-3 hours
- Testing: 1-2 hours
- Total: 3-5 hours (S/M task)
