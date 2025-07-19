"""
Custom logging handler for Rich console output during progress display.
"""

import logging
from typing import Optional
from rich.console import Console


class RichConsoleHandler(logging.Handler):
    """Logging handler that outputs through Rich console"""
    
    def __init__(self, console: Console, live=None):
        super().__init__()
        self.console = console
        self.live = live
        
    def emit(self, record):
        """Emit a log record through Rich console"""
        try:
            msg = self.format(record)
            
            # Color based on level
            if record.levelno >= logging.ERROR:
                style = "red"
            elif record.levelno >= logging.WARNING:
                style = "yellow"
            elif record.levelno >= logging.INFO:
                style = "cyan"
            else:
                style = "dim"
            
            # If we have a Live display, print through it
            if self.live:
                self.console.print(f"[{style}]{msg}[/{style}]")
            else:
                # Otherwise print directly
                self.console.print(f"[{style}]{msg}[/{style}]")
                
        except Exception:
            self.handleError(record)