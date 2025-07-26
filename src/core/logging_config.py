"""
Logging configuration for the Instagram auto signup system.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


class LoggingManager:
    """Centralized logging manager for the application."""
    
    def __init__(self, log_dir: str = "logs", log_level: str = "INFO"):
        self.log_dir = Path(log_dir)
        self.log_level = getattr(logging, log_level.upper())
        self.loggers = {}
        self._setup_logging_directory()
    
    def _setup_logging_directory(self) -> None:
        """Create logging directory if it doesn't exist."""
        self.log_dir.mkdir(exist_ok=True)
    
    def get_logger(self, name: str, log_file: Optional[str] = None) -> logging.Logger:
        """Get or create a logger with the specified name."""
        if name in self.loggers:
            return self.loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(self.log_level)
        
        # Prevent duplicate handlers
        if logger.handlers:
            return logger
        
        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            file_path = self.log_dir / log_file
        else:
            file_path = self.log_dir / f"{name}.log"
        
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(self.log_level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Error file handler for errors and above
        error_file_path = self.log_dir / f"{name}_errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_file_path,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        logger.addHandler(error_handler)
        
        self.loggers[name] = logger
        return logger
    
    def set_log_level(self, level: str) -> None:
        """Set log level for all loggers."""
        self.log_level = getattr(logging, level.upper())
        for logger in self.loggers.values():
            logger.setLevel(self.log_level)
            for handler in logger.handlers:
                handler.setLevel(self.log_level)


# Global logging manager instance
logging_manager = LoggingManager()


def get_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """Convenience function to get a logger."""
    return logging_manager.get_logger(name, log_file)