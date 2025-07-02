"""PDF source implementations."""

from .openreview_collector import OpenReviewPDFCollector
from .venue_mappings import OPENREVIEW_VENUES, get_venue_invitation, is_venue_supported
from .pmlr_collector import PMLRCollector
from .pubmed_central_collector import PubMedCentralCollector
from .acl_anthology_collector import ACLAnthologyCollector

__all__ = [
    "OpenReviewPDFCollector",
    "OPENREVIEW_VENUES",
    "get_venue_invitation",
    "is_venue_supported",
    "PMLRCollector",
    "PubMedCentralCollector",
    "ACLAnthologyCollector"
]
