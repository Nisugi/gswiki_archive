#!/usr/bin/env python3
"""
Filename utilities for wiki archive scripts.

Converts between wiki page titles and safe filenames.
"""


def title_to_filename(title: str) -> str:
    """
    Convert a wiki page title to a safe filename.

    Args:
        title: Wiki page title (e.g., "Category:Weapons")

    Returns:
        Safe filename with .html extension (e.g., "Category_COLON_Weapons.html")
    """
    safe = title.replace("/", "_SLASH_")
    safe = safe.replace("\\", "_BACKSLASH_")
    safe = safe.replace(":", "_COLON_")
    safe = safe.replace("*", "_STAR_")
    safe = safe.replace("?", "_QUESTION_")
    safe = safe.replace('"', "_QUOTE_")
    safe = safe.replace("<", "_LT_")
    safe = safe.replace(">", "_GT_")
    safe = safe.replace("|", "_PIPE_")
    return safe + ".html"


def filename_to_title(filename: str) -> str:
    """
    Convert a filename back to a wiki page title.

    Args:
        filename: Safe filename (e.g., "Category_COLON_Weapons.html")

    Returns:
        Wiki page title (e.g., "Category:Weapons")
    """
    title = filename.replace(".html", "")
    title = title.replace("_SLASH_", "/")
    title = title.replace("_BACKSLASH_", "\\")
    title = title.replace("_COLON_", ":")
    title = title.replace("_STAR_", "*")
    title = title.replace("_QUESTION_", "?")
    title = title.replace("_QUOTE_", '"')
    title = title.replace("_LT_", "<")
    title = title.replace("_GT_", ">")
    title = title.replace("_PIPE_", "|")
    return title
