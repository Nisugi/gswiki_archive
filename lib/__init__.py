"""
Shared library for wiki archive scripts.

Provides:
- WikiAPI: MediaWiki API client with rate limiting and retries
- setup_logging: Logging configuration for console and file output
- title_to_filename/filename_to_title: Safe filename conversion
"""

from lib.logging_config import setup_logging, get_log_dir
from lib.wiki_api import WikiAPI
from lib.filename_utils import title_to_filename, filename_to_title

__all__ = [
    "WikiAPI",
    "setup_logging",
    "get_log_dir",
    "title_to_filename",
    "filename_to_title",
]
