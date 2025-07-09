"""Conference scrapers for collecting papers from conference proceedings websites"""

from .ijcai_scraper import IJCAIScraper
from .acl_anthology_scraper import ACLAnthologyScraper

__all__ = ["IJCAIScraper", "ACLAnthologyScraper"]