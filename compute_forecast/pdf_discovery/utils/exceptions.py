"""Custom exceptions for PDF discovery operations."""

from typing import Optional


class PDFDiscoveryError(Exception):
    """Base exception for PDF discovery operations."""

    pass


class APIError(PDFDiscoveryError):
    """Exception raised when API requests fail."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
    ):
        """Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code if applicable
            response_text: Response body text if available
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class NoResultsError(PDFDiscoveryError):
    """Exception raised when no search results are found."""

    def __init__(self, message: str, query: Optional[str] = None):
        """Initialize no results error.

        Args:
            message: Error message
            query: Search query that yielded no results
        """
        super().__init__(message)
        self.query = query


class NoPDFFoundError(PDFDiscoveryError):
    """Exception raised when results exist but no PDF is available."""

    def __init__(self, message: str, results_count: Optional[int] = None):
        """Initialize no PDF found error.

        Args:
            message: Error message
            results_count: Number of results that were checked
        """
        super().__init__(message)
        self.results_count = results_count


class RateLimitError(PDFDiscoveryError):
    """Exception raised when rate limits are exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Suggested retry delay in seconds
        """
        super().__init__(message)
        self.retry_after = retry_after
