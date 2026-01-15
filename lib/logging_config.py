#!/usr/bin/env python3
"""
Logging configuration for wiki archive scripts.

Sets up logging to both console and file with rotation.

Usage:
    from lib.logging_config import setup_logging

    logger = setup_logging(
        name="import-content",
        wiki_id="gswiki",
        log_dir="/var/log",  # Optional, defaults to ./logs
    )
    logger.info("Starting import...")
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_logging(
    name: str,
    wiki_id: Optional[str] = None,
    log_dir: Optional[str] = None,
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    console: bool = True,
) -> logging.Logger:
    """
    Set up logging to console and file.

    Args:
        name: Logger name (used in log filename)
        wiki_id: Wiki identifier for log filename (e.g., "gswiki")
        log_dir: Directory for log files (default: ./logs or LOG_DIR env var)
        level: Logging level (default: INFO)
        max_bytes: Max log file size before rotation
        backup_count: Number of rotated log files to keep
        console: Whether to also log to console

    Returns:
        Configured logger instance

    Log files are named: {wiki_id}-{name}.log (e.g., gswiki-import.log)
    """
    # Determine log directory
    if log_dir is None:
        log_dir = os.environ.get("LOG_DIR", "./logs")

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Build log filename
    if wiki_id:
        log_filename = f"{wiki_id}-{name}.log"
    else:
        log_filename = f"{name}.log"

    log_file = log_path / log_filename

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear any existing handlers (for re-initialization)
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    logger.info(f"Logging initialized: {log_file}")
    return logger


def get_log_dir(default: str = "./logs") -> Path:
    """
    Get the log directory from environment or default.

    Checks LOG_DIR environment variable first.
    """
    return Path(os.environ.get("LOG_DIR", default))
