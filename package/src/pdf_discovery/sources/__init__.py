"""PDF source implementations."""

from .openreview_collector import OpenReviewPDFCollector
from .venue_mappings import OPENREVIEW_VENUES, get_venue_invitation, is_venue_supported
from .pmlr_collector import PMLRCollector
from .pubmed_central_collector import PubMedCentralCollector
from .acl_anthology_collector import ACLAnthologyCollector
from .openalex_collector import OpenAlexPDFCollector
from .cvf_collector import CVFCollector
from .aaai_collector import AAICollector
from .nature_collector import NaturePDFCollector
from .arxiv_collector import ArXivPDFCollector
from .semantic_scholar_collector import SemanticScholarPDFCollector
from .doi_resolver_collector import DOIResolverCollector
from .jmlr_collector import JMLRCollector
from .core_collector import COREPDFCollector
from .hal_collector import HALPDFCollector

__all__ = [
    "OpenReviewPDFCollector",
    "OPENREVIEW_VENUES",
    "get_venue_invitation",
    "is_venue_supported",
    "PMLRCollector",
    "PubMedCentralCollector",
    "ACLAnthologyCollector",
    "OpenAlexPDFCollector",
    "CVFCollector",
    "AAICollector",
    "NaturePDFCollector",
    "ArXivPDFCollector",
    "SemanticScholarPDFCollector",
    "DOIResolverCollector",
    "JMLRCollector",
    "COREPDFCollector",
    "HALPDFCollector"
]
