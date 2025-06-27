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