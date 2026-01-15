#!/usr/bin/env python3
"""
Wiki Archive - Content Import Script

Fetches pages from a source wiki via API and imports them into the local
MediaWiki archive. Designed for multiple wikis (GSWiki, Elanthipedia, etc.)
by sourcing the appropriate config before running.

Imports ALL pages, including user and talk pages, plus redirects.

Usage (after `source server/config/<wiki>.conf`):
    python3 server/import-content.py --full      # Full import of all pages
    python3 server/import-content.py --recent    # Import recent changes only
    python3 server/import-content.py --templates # Templates, categories, MediaWiki pages only
    python3 server/import-content.py --images    # Import images
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path for shared lib
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.wiki_api import WikiAPI
from lib.logging_config import setup_logging


def env_or_exit(name: str, default=None):
    """Fetch an environment variable or exit with a helpful message."""
    value = os.environ.get(name, default)
    if value is None:
        print(f"ERROR: {name} is not set. Source server/config/<wiki>.conf first.")
        sys.exit(1)
    return value


# Configuration from environment (with defaults for paths)
WIKI_ID = env_or_exit("WIKI_ID")
WIKI_NAME = env_or_exit("WIKI_NAME")
SOURCE_API = env_or_exit("SOURCE_API")
LOCAL_WIKI_DIR = env_or_exit("WIKI_DIR", "/var/www/gswiki-archive")
DELAY_SECONDS = float(env_or_exit("DELAY_SECONDS", "2"))
BATCH_SIZE = int(env_or_exit("BATCH_SIZE", "50"))

# Configurable paths with defaults
TMP_DIR = Path(os.environ.get("TMP_DIR", "/tmp"))
LOG_DIR = Path(os.environ.get("LOG_DIR", "/var/log"))

# Derived paths
LOCAL_SETTINGS = Path(LOCAL_WIKI_DIR) / "LocalSettings.php"
ARCHIVE_DATE_FILE = Path(LOCAL_WIKI_DIR) / ".archive-date"

# Set up logging
logger = setup_logging(
    name="import",
    wiki_id=WIKI_ID,
    log_dir=str(LOG_DIR),
)

# Set up API client
api = WikiAPI(
    api_url=SOURCE_API,
    wiki_name=WIKI_NAME,
    delay=DELAY_SECONDS,
    logger=logger,
)


def disable_read_only():
    """Temporarily disable read-only mode for import."""
    logger.info("Disabling read-only mode for import...")
    try:
        content = LOCAL_SETTINGS.read_text()
        new_content = content.replace('$wgReadOnly =', '# $wgReadOnly =')
        LOCAL_SETTINGS.write_text(new_content)
        return True
    except Exception as e:
        logger.warning(f"Could not disable read-only: {e}")
        return False


def enable_read_only():
    """Re-enable read-only mode after import."""
    logger.info("Re-enabling read-only mode...")
    try:
        content = LOCAL_SETTINGS.read_text()
        new_content = content.replace('# $wgReadOnly =', '$wgReadOnly =')
        LOCAL_SETTINGS.write_text(new_content)
        return True
    except Exception as e:
        logger.warning(f"Could not re-enable read-only: {e}")
        return False


def update_archive_date():
    """Update the archive date marker file."""
    logger.info("Updating archive date...")
    try:
        ARCHIVE_DATE_FILE.write_text(datetime.now().strftime('%b %d, %Y'))
    except Exception as e:
        logger.warning(f"Could not update archive date: {e}")


def import_xml(xml_content: str) -> bool:
    """Import XML content into local MediaWiki."""
    tmp_file = TMP_DIR / f"{WIKI_ID}-import.xml"
    tmp_file.write_text(xml_content, encoding="utf-8")

    result = subprocess.run(
        ["php", f"{LOCAL_WIKI_DIR}/maintenance/importDump.php", str(tmp_file)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        logger.error(f"Import error: {result.stderr}")
        return False

    return True


def import_batch(titles: list[str], batch_num: int, total_batches: int) -> tuple[int, int]:
    """Import a batch of pages. Returns (imported_count, failed_count)."""
    logger.info(f"[Batch {batch_num}/{total_batches}] Exporting {len(titles)} pages...")

    try:
        xml = api.export_pages(titles)
        if xml and import_xml(xml):
            logger.info(f"  Imported {len(titles)} pages")
            return len(titles), 0
        else:
            logger.error(f"  Failed to import batch")
            return 0, len(titles)
    except Exception as e:
        logger.error(f"  Batch failed: {e}")
        return 0, len(titles)


def run_maintenance():
    """Run MediaWiki maintenance scripts after import."""
    logger.info("Rebuilding search index...")
    subprocess.run(["php", f"{LOCAL_WIKI_DIR}/maintenance/rebuildtextindex.php"])

    logger.info("Refreshing links...")
    subprocess.run(["php", f"{LOCAL_WIKI_DIR}/maintenance/refreshLinks.php"])


def full_import():
    """Perform full import of all pages (including user/talk and redirects)."""
    logger.info("=== FULL IMPORT ===")

    pages = api.get_page_titles()
    logger.info(f"Pages to import: {len(pages)}")

    total_batches = (len(pages) + BATCH_SIZE - 1) // BATCH_SIZE
    imported = 0
    failed = 0

    for i in range(0, len(pages), BATCH_SIZE):
        batch = pages[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        batch_imported, batch_failed = import_batch(batch, batch_num, total_batches)
        imported += batch_imported
        failed += batch_failed

    logger.info(f"=== IMPORT COMPLETE === Imported: {imported}, Failed: {failed}")
    run_maintenance()


def templates_import():
    """Import only templates, MediaWiki pages, and categories (not main articles)."""
    logger.info("=== IMPORTING TEMPLATES & MEDIAWIKI PAGES ===")

    # Only non-article namespaces: 4=Project, 6=File, 8=MediaWiki, 10=Template, 14=Category
    namespaces = [4, 6, 8, 10, 14]
    pages = api.get_page_titles(namespaces=namespaces)
    logger.info(f"Pages to import: {len(pages)}")

    total_batches = (len(pages) + BATCH_SIZE - 1) // BATCH_SIZE
    imported = 0
    failed = 0

    for i in range(0, len(pages), BATCH_SIZE):
        batch = pages[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        batch_imported, batch_failed = import_batch(batch, batch_num, total_batches)
        imported += batch_imported
        failed += batch_failed

    logger.info(f"=== IMPORT COMPLETE === Imported: {imported}, Failed: {failed}")


def recent_import():
    """Import only recently changed pages."""
    logger.info("=== IMPORTING RECENT CHANGES ===")

    # Get recent changes (API default is last 30 days)
    from datetime import timezone
    # Use a date far in the past to get all recent changes the API will give us
    since = "2000-01-01T00:00:00Z"
    titles = list(api.get_recent_changes(since))

    logger.info(f"Recent pages to import: {len(titles)}")

    if not titles:
        logger.info("No changes to import")
        return

    total_batches = (len(titles) + BATCH_SIZE - 1) // BATCH_SIZE
    imported = 0
    failed = 0

    for i in range(0, len(titles), BATCH_SIZE):
        batch = titles[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        batch_imported, batch_failed = import_batch(batch, batch_num, total_batches)
        imported += batch_imported
        failed += batch_failed

    logger.info(f"=== IMPORT COMPLETE === Imported: {imported}, Failed: {failed}")


def import_images():
    """Import images from source wiki."""
    logger.info("=== IMPORTING IMAGES ===")

    images = api.get_all_images()
    logger.info(f"Total images: {len(images)}")

    # Download images
    img_dir = Path(LOCAL_WIKI_DIR) / "images" / "imported"
    img_dir.mkdir(parents=True, exist_ok=True)

    for i, img in enumerate(images):
        name = img["name"]
        url = img["url"]

        logger.info(f"[{i+1}/{len(images)}] Downloading: {name}")

        try:
            time.sleep(DELAY_SECONDS)
            import requests
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            filepath = img_dir / name
            filepath.write_bytes(response.content)

        except Exception as e:
            logger.error(f"  Failed: {e}")

    # Import via maintenance script
    logger.info("Importing images into MediaWiki...")
    result = subprocess.run(
        ["php", f"{LOCAL_WIKI_DIR}/maintenance/importImages.php", str(img_dir)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        logger.error(f"Import error: {result.stderr}")
    else:
        logger.info("Images imported successfully")


def main():
    parser = argparse.ArgumentParser(description=f"Import {WIKI_NAME} content")
    parser.add_argument("--full", action="store_true", help="Full import of all pages")
    parser.add_argument("--recent", action="store_true", help="Import recent changes only")
    parser.add_argument("--images", action="store_true", help="Import images")
    parser.add_argument("--templates", action="store_true", help="Import only templates, MediaWiki pages, categories (fast)")
    args = parser.parse_args()

    if not any([args.full, args.recent, args.images, args.templates]):
        parser.print_help()
        sys.exit(1)

    logger.info(f"{WIKI_NAME} Archive - Content Import")
    logger.info("=" * 50)

    # Disable read-only mode for import
    disable_read_only()

    try:
        if args.full:
            full_import()

        if args.templates:
            templates_import()

        if args.recent:
            recent_import()

        if args.images:
            import_images()

        # Update the archive date after successful import
        update_archive_date()
    finally:
        # Always re-enable read-only mode, even if import fails
        enable_read_only()


if __name__ == "__main__":
    main()
