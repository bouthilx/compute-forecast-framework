"""
Title normalizer for deduplication system.
Handles title normalization and similarity calculation for paper deduplication.
"""
import re
import string
from typing import Dict, Set, List
import logging
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

class TitleNormalizer:
    """
    Title normalization for paper comparison and deduplication.
    Implements exact interface contract from Issue #7.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common abbreviations and their expansions
        self.abbreviation_map = {
            # Technical terms
            'AI': 'Artificial Intelligence',
            'ML': 'Machine Learning', 
            'DL': 'Deep Learning',
            'RL': 'Reinforcement Learning',
            'NLP': 'Natural Language Processing',
            'CV': 'Computer Vision',
            'CNN': 'Convolutional Neural Network',
            'RNN': 'Recurrent Neural Network',
            'LSTM': 'Long Short-Term Memory',
            'GAN': 'Generative Adversarial Network',
            'VAE': 'Variational Autoencoder',
            'GPU': 'Graphics Processing Unit',
            'CPU': 'Central Processing Unit',
            'API': 'Application Programming Interface',
            'HTTP': 'Hypertext Transfer Protocol',
            'URL': 'Uniform Resource Locator',
            'SQL': 'Structured Query Language',
            'XML': 'Extensible Markup Language',
            'JSON': 'JavaScript Object Notation',
            'REST': 'Representational State Transfer',
            'IoT': 'Internet of Things',
            'AR': 'Augmented Reality',
            'VR': 'Virtual Reality',
            
            # Mathematical terms
            'PDE': 'Partial Differential Equation',
            'ODE': 'Ordinary Differential Equation',
            'SVM': 'Support Vector Machine',
            'KNN': 'K-Nearest Neighbors',
            'PCA': 'Principal Component Analysis',
            'ICA': 'Independent Component Analysis',
            'GMM': 'Gaussian Mixture Model',
            'HMM': 'Hidden Markov Model',
            'MDP': 'Markov Decision Process',
            'EM': 'Expectation Maximization',
            'SGD': 'Stochastic Gradient Descent',
            'MCMC': 'Markov Chain Monte Carlo',
            
            # Research terms
            'vs': 'versus',
            'w/': 'with',
            'w/o': 'without',
            '&': 'and',
            '+': 'plus',
            
            # Units and measurements
            '2D': 'two dimensional',
            '3D': 'three dimensional',
            '4D': 'four dimensional',
            'MB': 'megabyte',
            'GB': 'gigabyte',
            'TB': 'terabyte',
            'MHz': 'megahertz',
            'GHz': 'gigahertz',
            'RAM': 'Random Access Memory',
            'ROM': 'Read Only Memory',
        }
        
        # Stop words to remove
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'via', 'using', 'through', 'under',
            'over', 'into', 'onto', 'upon', 'within', 'without', 'during',
            'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off',
            'about', 'against', 'between', 'among', 'through', 'around'
        }
        
        # Common title noise patterns to remove
        self.noise_patterns = [
            r'\[\s*[^]]*\s*\]',  # [anything in brackets]
            r'\(\s*[^)]*\s*\)',  # (anything in parentheses) 
            r'\{[^}]*\}',        # {anything in braces}
            r'["\']',            # quotes
            r'[\u2018\u2019\u201c\u201d]',  # smart quotes
            r':\s*[^:]*$',       # subtitle after colon (often venue/year info)
            r'\s*-\s*[^-]*$',    # subtitle after dash
            r'\s*\|\s*[^|]*$',   # subtitle after pipe
            r'\s*\.\s*[^.]*$',   # subtitle after period
            r'\bpreprint\b',     # "preprint"
            r'\barxiv\b',        # "arxiv"
            r'\bversion\s+\d+',  # "version 1", "version 2", etc.
            r'\bv\d+\b',         # "v1", "v2", etc.
            r'\bdraft\b',        # "draft"
            r'\bupdated?\b',     # "update", "updated"
            r'\brevised?\b',     # "revise", "revised"
        ]
        
        # Roman numerals pattern
        self.roman_pattern = re.compile(r'\b(?=[MDCLXVI])M{0,4}(CM|CD|D?C{0,3})?(XC|XL|L?X{0,3})?(IX|IV|V?I{0,3})?\b')
    
    def normalize_title(self, title: str) -> str:
        """
        Normalize title for comparison
        
        REQUIREMENTS:
        - Remove punctuation and extra whitespace
        - Convert to lowercase
        - Handle common abbreviations
        - Remove year suffixes
        - Handle special characters and unicode
        """
        if not title:
            return ""
        
        # Step 1: Initial cleaning
        normalized = title.strip()
        
        # Step 2: Remove noise patterns
        for pattern in self.noise_patterns:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Step 3: Convert to lowercase
        normalized = normalized.lower()
        
        # Step 4: Remove punctuation but preserve spaces
        # Keep hyphens and apostrophes for now
        normalized = re.sub(r'[^\w\s\'-]', ' ', normalized)
        
        # Step 5: Handle abbreviations
        words = normalized.split()
        expanded_words = []
        for word in words:
            # Remove punctuation from word for lookup
            clean_word = re.sub(r'[^\w]', '', word).upper()
            if clean_word in self.abbreviation_map:
                expanded_words.extend(self.abbreviation_map[clean_word].lower().split())
            else:
                # Keep original word but clean it
                clean_word = re.sub(r'[^\w]', '', word).lower()
                if clean_word:  # Only add non-empty words
                    expanded_words.append(clean_word)
        
        # Step 6: Remove stop words
        filtered_words = [word for word in expanded_words if word not in self.stop_words]
        
        # Step 7: Remove numbers and single characters (except 'a')
        filtered_words = [
            word for word in filtered_words 
            if not (word.isdigit() or (len(word) == 1 and word != 'a'))
        ]
        
        # Step 8: Handle Roman numerals (convert to numbers)
        processed_words = []
        for word in filtered_words:
            if self.roman_pattern.fullmatch(word.upper()):
                # Convert Roman numeral to Arabic number
                try:
                    number = self._roman_to_int(word.upper())
                    processed_words.append(str(number))
                except:
                    processed_words.append(word)
            else:
                processed_words.append(word)
        
        # Step 9: Sort words for order-independent comparison
        # But try to preserve some structure by keeping first few words in order
        if len(processed_words) <= 3:
            # For short titles, preserve order
            normalized = ' '.join(processed_words)
        else:
            # For longer titles, keep first 2 words in order, sort the rest
            first_words = processed_words[:2]
            other_words = sorted(processed_words[2:])
            normalized = ' '.join(first_words + other_words)
        
        # Step 10: Final cleanup
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate title similarity score (0.0 to 1.0)
        
        REQUIREMENTS:
        - Use Levenshtein distance with normalization
        - Handle abbreviations and synonyms
        - Account for word order differences
        - Complete within 5ms per comparison
        """
        if not title1 or not title2:
            return 0.0
        
        # Normalize both titles
        norm1 = self.normalize_title(title1)
        norm2 = self.normalize_title(title2)
        
        # Exact match after normalization
        if norm1 == norm2:
            return 1.0
        
        # Use multiple similarity measures
        # Token sort ratio: order-independent word comparison
        token_sort_ratio = fuzz.token_sort_ratio(norm1, norm2) / 100.0
        
        # Token set ratio: unique word set comparison
        token_set_ratio = fuzz.token_set_ratio(norm1, norm2) / 100.0
        
        # Partial ratio: substring matching
        partial_ratio = fuzz.partial_ratio(norm1, norm2) / 100.0
        
        # Regular ratio: character-level similarity
        ratio = fuzz.ratio(norm1, norm2) / 100.0
        
        # Weighted combination favoring token-based measures
        similarity = (
            token_sort_ratio * 0.4 +
            token_set_ratio * 0.3 +
            partial_ratio * 0.2 +
            ratio * 0.1
        )
        
        return similarity
    
    def _roman_to_int(self, roman: str) -> int:
        """Convert Roman numeral to integer"""
        values = {
            'I': 1, 'V': 5, 'X': 10, 'L': 50,
            'C': 100, 'D': 500, 'M': 1000
        }
        
        total = 0
        prev_value = 0
        
        for char in reversed(roman):
            value = values[char]
            if value < prev_value:
                total -= value
            else:
                total += value
            prev_value = value
        
        return total
    
    def get_title_tokens(self, title: str) -> Set[str]:
        """Get normalized tokens from title for indexing"""
        normalized = self.normalize_title(title)
        return set(normalized.split())
    
    def preprocess_titles_for_similarity(self, titles: List[str]) -> Dict[str, str]:
        """Batch preprocess titles for efficient similarity calculation"""
        return {title: self.normalize_title(title) for title in titles}
    
    def find_similar_titles(self, 
                          target_title: str, 
                          candidate_titles: List[str], 
                          threshold: float = 0.9) -> List[tuple]:
        """
        Find similar titles above threshold
        
        Returns list of (title, similarity_score) tuples sorted by similarity
        """
        if not target_title or not candidate_titles:
            return []
        
        similarities = []
        for candidate in candidate_titles:
            similarity = self.calculate_title_similarity(target_title, candidate)
            if similarity >= threshold:
                similarities.append((candidate, similarity))
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities
    
    def is_title_variant(self, title1: str, title2: str, threshold: float = 0.95) -> bool:
        """Check if two titles are variants of each other"""
        return self.calculate_title_similarity(title1, title2) >= threshold
    
    def extract_core_title(self, title: str) -> str:
        """Extract core title by removing common suffixes and prefixes"""
        if not title:
            return ""
        
        core = title.strip()
        
        # Remove common prefixes
        prefixes_to_remove = [
            r'^on\s+',
            r'^towards?\s+',
            r'^improving\s+',
            r'^learning\s+',
            r'^understanding\s+',
            r'^a\s+study\s+of\s+',
            r'^an?\s+analysis\s+of\s+',
            r'^an?\s+approach\s+to\s+',
            r'^an?\s+method\s+for\s+',
        ]
        
        for prefix in prefixes_to_remove:
            core = re.sub(prefix, '', core, flags=re.IGNORECASE)
        
        # Remove common suffixes
        suffixes_to_remove = [
            r'\s+and\s+applications?$',
            r'\s+and\s+beyond$',
            r'\s+revisited$',
            r'\s+with\s+applications?$',
            r'\s+in\s+practice$',
            r'\s+a\s+survey$',
            r'\s+a\s+review$',
        ]
        
        for suffix in suffixes_to_remove:
            core = re.sub(suffix, '', core, flags=re.IGNORECASE)
        
        return core.strip()


class TitleSimilarityCache:
    """LRU cache for title similarity calculations to improve performance"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache: Dict[tuple, float] = {}
        self.access_order: List[tuple] = []
    
    def get_similarity(self, title1: str, title2: str) -> float:
        """Get cached similarity or None if not cached"""
        # Ensure consistent ordering for cache key
        key = (title1, title2) if title1 <= title2 else (title2, title1)
        
        if key in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        
        return None
    
    def set_similarity(self, title1: str, title2: str, similarity: float) -> None:
        """Cache similarity score"""
        # Ensure consistent ordering for cache key
        key = (title1, title2) if title1 <= title2 else (title2, title1)
        
        if key in self.cache:
            # Update existing entry
            self.cache[key] = similarity
            self.access_order.remove(key)
            self.access_order.append(key)
        else:
            # Add new entry
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                lru_key = self.access_order.pop(0)
                del self.cache[lru_key]
            
            self.cache[key] = similarity
            self.access_order.append(key)
    
    def clear(self) -> None:
        """Clear the cache"""
        self.cache.clear()
        self.access_order.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'utilization': len(self.cache) / self.max_size
        }