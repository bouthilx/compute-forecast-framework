class PaperCollectionError(Exception):
    """Base exception for paper collection system"""
    pass

class APIError(PaperCollectionError):
    """Error accessing external APIs"""
    pass

class ValidationError(PaperCollectionError):
    """Error in data validation"""
    pass

class ConfigurationError(PaperCollectionError):
    """Error in configuration"""
    pass

class WorkerError(PaperCollectionError):
    """Error in worker execution"""
    pass


# PDF Discovery specific exceptions
class PDFDiscoveryError(PaperCollectionError):
    """Base exception for PDF discovery operations"""
    pass


class PDFNotAvailableError(PDFDiscoveryError):
    """Raised when a PDF is not available for a paper"""
    pass


class UnsupportedSourceError(PDFDiscoveryError):
    """Raised when a paper is from an unsupported source/venue"""
    pass


class PDFNetworkError(PDFDiscoveryError):
    """Raised when network operations fail during PDF discovery"""
    pass