"""Tests for PDF extraction validation logic."""


from src.pdf_parser.core.validation import AffiliationValidator


class TestAffiliationValidator:
    """Test affiliation validation logic."""
    
    def test_validator_initialization(self):
        """Test validator can be initialized."""
        validator = AffiliationValidator()
        assert validator is not None
    
    def test_validate_basic_affiliations(self):
        """Test validation of basic affiliation extraction."""
        validator = AffiliationValidator()
        
        extraction_result = {
            'text': 'Authors: John Doe (University of Test)',
            'method': 'test_extractor',
            'confidence': 0.8,
            'affiliations': [
                {'name': 'University of Test', 'country': 'USA'}
            ]
        }
        
        paper_metadata = {
            'title': 'Test Paper',
            'authors': ['John Doe']
        }
        
        is_valid = validator.validate_affiliations(extraction_result, paper_metadata)
        assert is_valid is True
    
    def test_reject_empty_affiliations(self):
        """Test rejection of empty affiliation results."""
        validator = AffiliationValidator()
        
        extraction_result = {
            'text': 'Some text without affiliations',
            'method': 'test_extractor', 
            'confidence': 0.9,
            'affiliations': []
        }
        
        paper_metadata = {'title': 'Test Paper'}
        
        is_valid = validator.validate_affiliations(extraction_result, paper_metadata)
        assert is_valid is False
    
    def test_reject_low_confidence(self):
        """Test rejection of low confidence extractions."""
        validator = AffiliationValidator()
        
        extraction_result = {
            'text': 'Authors: John Doe (University of Test)',
            'method': 'test_extractor',
            'confidence': 0.3,  # Low confidence
            'affiliations': [
                {'name': 'University of Test', 'country': 'USA'}
            ]
        }
        
        paper_metadata = {'title': 'Test Paper'}
        
        is_valid = validator.validate_affiliations(extraction_result, paper_metadata)
        assert is_valid is False
    
    def test_validate_with_author_matching(self):
        """Test validation that checks author name matching."""
        validator = AffiliationValidator()
        
        extraction_result = {
            'text': 'Authors: John Doe (MIT), Jane Smith (Stanford)',
            'method': 'test_extractor',
            'confidence': 0.8,
            'affiliations': [
                {'name': 'MIT', 'country': 'USA'},
                {'name': 'Stanford', 'country': 'USA'}
            ]
        }
        
        # Metadata with matching authors
        paper_metadata = {
            'title': 'Test Paper',
            'authors': ['John Doe', 'Jane Smith']
        }
        
        is_valid = validator.validate_affiliations(extraction_result, paper_metadata)
        assert is_valid is True
    
    def test_validate_minimum_affiliation_count(self):
        """Test validation requires minimum number of affiliations."""
        validator = AffiliationValidator(min_affiliations=2)
        
        # Only one affiliation but validator requires 2
        extraction_result = {
            'text': 'Author: John Doe (MIT)',
            'method': 'test_extractor',
            'confidence': 0.8,
            'affiliations': [
                {'name': 'MIT', 'country': 'USA'}
            ]
        }
        
        paper_metadata = {'title': 'Test Paper'}
        
        is_valid = validator.validate_affiliations(extraction_result, paper_metadata)
        assert is_valid is False
    
    def test_validate_text_quality(self):
        """Test validation of extracted text quality."""
        validator = AffiliationValidator()
        
        # Poor quality text (very short)
        extraction_result = {
            'text': 'abc',  # Too short
            'method': 'test_extractor',
            'confidence': 0.8,
            'affiliations': [
                {'name': 'MIT', 'country': 'USA'}
            ]
        }
        
        paper_metadata = {'title': 'Test Paper'}
        
        is_valid = validator.validate_affiliations(extraction_result, paper_metadata)
        assert is_valid is False