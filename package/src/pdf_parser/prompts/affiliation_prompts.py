"""Affiliation extraction prompts for Claude Vision API."""

AFFILIATION_EXTRACTION_PROMPT = """
Please extract author names and their institutional affiliations from this research paper.

Look for:
1. Author names (usually at the top of the first page)
2. Their affiliated institutions (universities, companies, research labs)
3. The mapping between authors and institutions (often indicated by superscripts, footnotes, or symbols)
4. Email addresses if visible

Return as JSON:
{
    "authors_with_affiliations": [
        {"name": "Author Name", "affiliation": "Institution Name", "email": "optional@email.com"},
        ...
    ],
    "all_affiliations": ["List of all unique institutions found"],
    "confidence": 0.0-1.0
}

Guidelines:
- Return confidence 0.9+ only if you can clearly see authors and affiliations
- Return confidence 0.7-0.8 if some information is unclear but mostly extractable  
- Return confidence 0.5-0.6 if only partial information is available
- Return confidence below 0.5 if affiliations are not clearly visible
- If you cannot find clear affiliations, return empty lists with low confidence
- Focus on institutional affiliations (universities, companies) not departments within institutions
"""

VALIDATION_PROMPT = """
Please validate the extracted affiliation information against the visible text in this research paper.

Original extraction:
{extraction}

Questions to verify:
1. Do the author names appear in the document?
2. Do the institutional affiliations match what's visible?
3. Are the author-affiliation mappings correct?
4. Is the confidence score appropriate for the clarity of the information?

Return validation as JSON:
{
    "is_valid": true/false,
    "issues": ["List any problems found"],
    "suggested_confidence": 0.0-1.0,
    "corrected_extraction": "Only if corrections needed, otherwise null"
}
"""

def build_affiliation_prompt(paper_title: str = None, known_authors: list = None) -> str:
    """Build contextualized affiliation extraction prompt.
    
    Args:
        paper_title: Title of the paper for context
        known_authors: List of known author names for validation
        
    Returns:
        Customized prompt string
    """
    base_prompt = AFFILIATION_EXTRACTION_PROMPT
    
    if paper_title:
        context = f"\nPaper title for context: \"{paper_title}\"\n"
        base_prompt = context + base_prompt
    
    if known_authors:
        author_context = f"\nExpected authors (for validation): {', '.join(known_authors)}\n"
        base_prompt = base_prompt + author_context
    
    return base_prompt

def build_validation_prompt(extraction_result: dict) -> str:
    """Build validation prompt with extraction results.
    
    Args:
        extraction_result: The extraction result to validate
        
    Returns:
        Validation prompt string
    """
    return VALIDATION_PROMPT.format(extraction=extraction_result)