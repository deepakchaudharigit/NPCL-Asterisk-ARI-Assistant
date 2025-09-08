"""
Logging configuration for voice assistant
"""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_logging_settings


def setup_logger(name: str = None) -> logging.Logger:
    """
    Setup logger with consistent configuration
    
    Args:
        name: Logger name (if None, uses root logger)
        
    Returns:
        Configured logger instance
    """
    logging_settings = get_logging_settings()
    
    # Get logger
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Set level
    logger.setLevel(getattr(logging, logging_settings.log_level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(logging_settings.log_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if logging_settings.log_file:
        log_file_path = Path(logging_settings.log_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name"""
    return logging.getLogger(name)