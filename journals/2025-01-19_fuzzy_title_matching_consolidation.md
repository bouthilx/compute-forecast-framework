# Fuzzy Title Matching for Consolidation Process

## 2025-01-19 - Analysis of Title Matching Requirements

### Problem Analysis

The current consolidation process uses exact title matching after basic normalization, which misses many valid matches between ArXiv preprints and their conference versions. Common title variations include:

1. **Punctuation differences**: Hyphens vs colons, different quote styles
2. **Subtitle variations**: ArXiv papers often have longer/different subtitles
3. **Minor word changes**: "A Method for" vs "Method for", "Towards" vs "Toward"
4. **Case and spacing differences**: Already handled by current normalization

### Current Implementation Analysis

#### OpenAlex Source (`openalex.py`)
- Uses `_similar_title()` method (line 259-263)
- Very basic: checks if normalized titles are equal or one contains the other
- No fuzzy matching, just substring containment

#### Semantic Scholar Source (`semantic_scholar.py`)
- Uses `_similar_title()` method (line 301-316)
- Also basic: exact match or substring containment after normalization
- No fuzzy matching capabilities

### Existing Fuzzy Matching Infrastructure

We already have robust fuzzy matching infrastructure in the codebase:

1. **`rapidfuzz` library** is already a dependency (used in fuzzy_venue_matcher.py and matchers.py)
2. **FuzzyVenueMatcher** (fuzzy_venue_matcher.py) provides sophisticated venue matching with:
   - Multiple similarity measures (token sort, partial, token set ratios)
   - Abbreviation handling
   - Normalization pipeline
3. **PaperFuzzyMatcher** (matchers.py) provides paper deduplication with:
   - Title similarity calculation using multiple measures
   - Author matching with initials handling
   - Venue/year matching

### Proposed Implementation Strategy

#### 1. Create a Shared Title Matcher Utility

Create a new file `compute_forecast/pipeline/consolidation/sources/title_matcher.py`:

```python
from rapidfuzz import fuzz
import re
from typing import Optional, Tuple, List

class TitleMatcher:
    """Fuzzy title matching for consolidation with safety mechanisms."""

    def __init__(
        self,
        exact_threshold: float = 1.0,
        high_confidence_threshold: float = 0.95,
        medium_confidence_threshold: float = 0.85,
        require_safety_checks: bool = True
    ):
        self.exact_threshold = exact_threshold
        self.high_confidence_threshold = high_confidence_threshold
        self.medium_confidence_threshold = medium_confidence_threshold
        self.require_safety_checks = require_safety_checks

        # Title normalization patterns
        self.title_suffixes = [
            r"\s*\(extended abstract\)",
            r"\s*\(short paper\)",
            r"\s*\(poster\)",
            r"\s*:\s*supplementary.*",
            # ArXiv-specific patterns
            r"\s*\[.*\]$",  # Remove bracketed content at end
        ]

    def normalize_title(self, title: str) -> str:
        """Normalize title for comparison."""
        if not title:
            return ""

        normalized = title.lower().strip()

        # Remove common suffixes
        for suffix_pattern in self.title_suffixes:
            normalized = re.sub(suffix_pattern, "", normalized, flags=re.IGNORECASE)

        # Normalize punctuation
        normalized = re.sub(r'[^\w\s]', ' ', normalized)

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        return normalized

    def calculate_similarity(
        self,
        title1: str,
        title2: str,
        year1: Optional[int] = None,
        year2: Optional[int] = None,
        authors1: Optional[List[str]] = None,
        authors2: Optional[List[str]] = None
    ) -> Tuple[float, str]:
        """
        Calculate title similarity with safety checks.

        Returns:
            (similarity_score, match_type)
            match_type: "exact", "high_confidence", "medium_confidence", "low_confidence", "no_match"
        """
        if not title1 or not title2:
            return 0.0, "no_match"

        norm1 = self.normalize_title(title1)
        norm2 = self.normalize_title(title2)

        # Exact match
        if norm1 == norm2:
            return 1.0, "exact"

        # Calculate multiple similarity measures
        token_sort = fuzz.token_sort_ratio(norm1, norm2) / 100.0
        token_set = fuzz.token_set_ratio(norm1, norm2) / 100.0
        partial = fuzz.partial_ratio(norm1, norm2) / 100.0
        ratio = fuzz.ratio(norm1, norm2) / 100.0

        # Weighted combination (favor token-based for academic titles)
        similarity = (
            token_sort * 0.4 +
            token_set * 0.3 +
            partial * 0.2 +
            ratio * 0.1
        )

        # Apply safety checks if enabled
        if self.require_safety_checks and similarity < self.exact_threshold:
            # Require year match for fuzzy matches
            if year1 and year2 and abs(year1 - year2) > 1:
                return similarity * 0.5, "low_confidence"

            # Check author overlap for medium confidence matches
            if similarity >= self.medium_confidence_threshold:
                if authors1 and authors2:
                    # Simple author overlap check
                    authors1_normalized = {a.lower().strip() for a in authors1}
                    authors2_normalized = {a.lower().strip() for a in authors2}
                    overlap = len(authors1_normalized & authors2_normalized)
                    if overlap == 0:
                        return similarity * 0.7, "low_confidence"

        # Determine match type
        if similarity >= self.high_confidence_threshold:
            return similarity, "high_confidence"
        elif similarity >= self.medium_confidence_threshold:
            return similarity, "medium_confidence"
        else:
            return similarity, "low_confidence" if similarity > 0.7 else "no_match"
```

#### 2. Update OpenAlex Source

Modify `openalex.py` to use the new fuzzy matcher:

```python
# Add import
from .title_matcher import TitleMatcher

# In __init__
self.title_matcher = TitleMatcher(
    high_confidence_threshold=0.90,  # Conservative for OpenAlex
    require_safety_checks=True
)

# Replace _similar_title method
def _similar_title(self, title1: str, title2: str, year1: int = None, year2: int = None) -> bool:
    """Check if two titles are similar using fuzzy matching."""
    similarity, match_type = self.title_matcher.calculate_similarity(
        title1, title2, year1, year2
    )
    # Accept high confidence matches and above
    return match_type in ["exact", "high_confidence"]
```

#### 3. Update Semantic Scholar Source

Similarly update `semantic_scholar.py`:

```python
# Add import
from .title_matcher import TitleMatcher

# In __init__
self.title_matcher = TitleMatcher(
    high_confidence_threshold=0.92,  # Slightly higher threshold for S2
    require_safety_checks=True
)

# Update _similar_title method to use fuzzy matching
```

#### 4. Safety Mechanisms

The proposed implementation includes several safety mechanisms:

1. **Configurable thresholds**: Different confidence levels for different use cases
2. **Year matching requirement**: Fuzzy matches require papers to be from same/adjacent years
3. **Author overlap check**: For medium confidence matches, require at least one common author
4. **Conservative defaults**: High thresholds by default to avoid false positives
5. **Match type reporting**: Returns both score and confidence level for logging/debugging

### Benefits

1. **Better ArXiv-Conference matching**: Handle common title variations between preprints and published versions
2. **Reduced manual intervention**: Fewer missed matches requiring manual consolidation
3. **Configurable safety**: Can adjust thresholds based on source reliability
4. **Reusable component**: Single implementation used by all sources
5. **Backward compatible**: Falls back to exact matching with high thresholds

### Testing Strategy

1. **Unit tests**: Test fuzzy matching with known ArXiv-conference paper pairs
2. **Integration tests**: Verify consolidation finds more matches without false positives
3. **Performance tests**: Ensure fuzzy matching doesn't significantly slow down consolidation
4. **Validation**: Manual review of fuzzy matches on sample datasets

### Implementation Priority

This is a **Medium priority** enhancement that would improve consolidation quality without major architectural changes. The implementation is straightforward given existing fuzzy matching infrastructure.
