"""Conference scrapers for collecting papers from conference proceedings websites"""

from .ijcai_scraper import IJCAIScraper
from .acl_anthology_scraper import ACLAnthologyScraper
from .cvf_scraper import CVFScraper
from .pmlr_scraper import PMLRScraper

__all__ = ["IJCAIScraper", "ACLAnthologyScraper", "CVFScraper", "PMLRScraper"]