"""
Logging configuration for the application.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.settings import DEBUG, LOG_LEVEL


def setup_logging():
    """
    Set up logging configuration.
    """
    log_dir = "logs"

    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "bot.log")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_format)

    # File handler
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_format)

    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Disable logs from libraries if not in debug mode
    if not DEBUG:
        logging.getLogger("aiogram").setLevel(logging.WARNING)
        logging.getLogger("facebook_business").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def get_logger(name: str):
    """
    Get a logger with the specified name.

    Args:
        name: The name of the logger.

    Returns:
        A configured logger instance.
    """
    return logging.getLogger(name)
