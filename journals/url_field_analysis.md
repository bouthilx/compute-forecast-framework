# URL Field Analysis for raw_collected_papers.json

**Timestamp**: 2025-07-01

## Summary of Findings

I examined the `raw_collected_papers.json` file to identify URL fields and other identifiers that could be used to access papers. Here are the key findings:

## Available Fields

The JSON file contains the following fields for each paper:
- `abstract`
- `authors` (with nested fields: `name`, `affiliation`, `author_id`, `email`)
- `citations`
- `collection_timestamp`
- `collection_year`
- `computational_analysis`
- `domain`
- `id`
- `mila_domain`
- `paper_id`
- `source`
- `title`
- `url`
- `venue`
- `venue_score`
- `venue_type`
- `year`

## URL Availability

1. **URL Field**: 617 papers have a `url` field populated (out of the total dataset)
2. **URL Format**: All URLs found are from Semantic Scholar with the pattern:
   - `https://www.semanticscholar.org/paper/[paper_hash]`
   - Example: `https://www.semanticscholar.org/paper/4f2eda8077dc7a69bb2b4e0a1a086cf054adb3f9`

3. **Paper ID Field**: The `paper_id` field exists but is mostly empty (`""`) in the dataset

4. **ID Field**: The `id` field contains the same hash values as found in the Semantic Scholar URLs (without the full URL)

## Other Identifiers

1. **Author IDs**: Some papers from OpenAlex source contain author IDs in the format:
   - `https://openalex.org/A[numeric_id]`
   - Example: `https://openalex.org/A5034622258`

2. **DOI/ArXiv**: I searched for DOI patterns and arxiv references in abstracts and found:
   - Some abstracts mention arxiv papers (e.g., "arXiv:2501.09209")
   - Some abstracts contain DOI patterns (e.g., "10." prefix)
   - However, these are not structured fields and would require parsing from abstract text

## Data Sources

Papers come from two main sources:
- `semantic_scholar`: These papers typically have URLs
- `openalex`: These papers typically don't have URLs in the dataset, but authors have OpenAlex IDs

## Recommendations for Accessing Papers

1. **For Semantic Scholar papers**: Use the provided URL directly or construct it using the `id` field
2. **For papers with arxiv mentions in abstracts**: Extract arxiv IDs from abstract text
3. **For papers with DOIs in abstracts**: Extract DOI patterns from abstract text
4. **For OpenAlex papers**: May need to use OpenAlex API with author IDs to find papers

## Sample Code to Access URLs

```python
import json

# Load the data
with open('data/raw_collected_papers.json', 'r') as f:
    papers = json.load(f)

# Get papers with URLs
papers_with_urls = [p for p in papers if p.get('url')]
print(f"Papers with URLs: {len(papers_with_urls)}")

# Get papers with IDs that can be used to construct URLs
papers_with_ids = [p for p in papers if p.get('id')]
print(f"Papers with IDs: {len(papers_with_ids)}")

# Construct Semantic Scholar URL from ID
def construct_semantic_scholar_url(paper_id):
    return f"https://www.semanticscholar.org/paper/{paper_id}"

# Extract potential arxiv/DOI from abstract
def extract_identifiers_from_abstract(abstract):
    import re
    arxiv_pattern = r'arXiv:(\d+\.\d+)'
    doi_pattern = r'10\.\d+/[^\s]+'
    
    arxiv_matches = re.findall(arxiv_pattern, abstract)
    doi_matches = re.findall(doi_pattern, abstract)
    
    return {
        'arxiv': arxiv_matches,
        'doi': doi_matches
    }
```

## Limitations

1. Not all papers have accessible URLs
2. The `paper_id` field is not consistently populated
3. DOIs and arxiv IDs would need to be extracted from unstructured text (abstracts)
4. Different data sources (Semantic Scholar vs OpenAlex) have different identifier schemes