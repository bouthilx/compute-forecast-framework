import logging
import sys
from pathlib import Path
from typing import Optional, List


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Setup centralized logging configuration"""

    # Create logs directory if it doesn't exist
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Setup handlers
    handlers: List[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        file_handler: logging.Handler = logging.FileHandler(log_file)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()), format=log_format, handlers=handlers
    )

    return logging.getLogger(__name__)
