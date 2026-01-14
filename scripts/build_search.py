#!/usr/bin/env python3
"""
GSWiki Archive Search Index Builder

Runs Pagefind to build a static search index for the archived wiki pages.
Pagefind must be installed: npm install -g pagefind
Or via npx: npx pagefind
"""

import json
import subprocess
import sys
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

DOCS_DIR = PROJECT_ROOT / CONFIG["output"]["docs_dir"]


def check_pagefind_installed():
    """Check if Pagefind is available."""
    try:
        result = subprocess.run(
            ["npx", "pagefind", "--version"],
            capture_output=True,
            text=True,
            shell=True
        )
        if result.returncode == 0:
            print(f"Pagefind version: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass

    print("ERROR: Pagefind is not installed.")
    print("Install it with: npm install -g pagefind")
    print("Or run with npx: npx pagefind")
    return False


def build_search_index():
    """Run Pagefind to build the search index."""
    print("Building search index with Pagefind...")
    print(f"Source: {DOCS_DIR}")

    # Pagefind command
    cmd = [
        "npx", "pagefind",
        "--site", str(DOCS_DIR),
        "--output-subdir", "search",
        # Only index the wiki pages, not the homepage or assets
        "--glob", "wiki/*.html",
    ]

    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            shell=True,
            capture_output=True,
            text=True
        )

        print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode == 0:
            print("\nSearch index built successfully!")
            print(f"Index location: {DOCS_DIR / 'search'}")
            return True
        else:
            print(f"\nERROR: Pagefind failed with return code {result.returncode}")
            return False

    except Exception as e:
        print(f"\nERROR: Failed to run Pagefind: {e}")
        return False


def main():
    """Main entry point."""
    print("GSWiki Archive Search Index Builder")
    print("=" * 50)

    if not check_pagefind_installed():
        sys.exit(1)

    if not DOCS_DIR.exists():
        print(f"ERROR: Docs directory not found: {DOCS_DIR}")
        print("Run crawl.py first to download wiki pages.")
        sys.exit(1)

    wiki_dir = DOCS_DIR / "wiki"
    if not wiki_dir.exists() or not any(wiki_dir.glob("*.html")):
        print(f"ERROR: No HTML files found in {wiki_dir}")
        print("Run crawl.py first to download wiki pages.")
        sys.exit(1)

    if build_search_index():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
