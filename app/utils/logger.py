"""
Logging Utility
================
Centralized logging configuration for the entire application.
Provides structured, colored console output and optional file logging.

Usage:
    from app.utils.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Server started")
"""

import logging
import sys
from typing import Optional


# ANSI color codes for terminal output
COLORS = {
    "DEBUG": "\033[36m",     # Cyan
    "INFO": "\033[32m",      # Green
    "WARNING": "\033[33m",   # Yellow
    "ERROR": "\033[31m",     # Red
    "CRITICAL": "\033[35m",  # Magenta
    "RESET": "\033[0m",
}


class ColoredFormatter(logging.Formatter):
    """Custom log formatter that adds color to log levels in terminal output."""

    def format(self, record: logging.LogRecord) -> str:
        color = COLORS.get(record.levelname, COLORS["RESET"])
        reset = COLORS["RESET"]
        record.levelname = f"{color}{record.levelname:<8}{reset}"
        return super().format(record)


def get_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Create and return a configured logger instance.

    Args:
        name: Logger name (use __name__ for module-level loggers).
        level: Log level string (DEBUG, INFO, WARNING, ERROR). Defaults to INFO.
        log_file: Optional path to write logs to a file.

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger

    log_level = getattr(logging, (level or "INFO").upper(), logging.INFO)
    logger.setLevel(log_level)

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = ColoredFormatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Optional file handler (plain text, no colors)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Prevent log messages from propagating to the root logger
    logger.propagate = False

    return logger
