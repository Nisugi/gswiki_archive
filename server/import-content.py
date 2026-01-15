#!/usr/bin/env python3
"""
GSWiki Archive - Content Import Script

Fetches pages from GSWiki via API and imports them into the local MediaWiki.
Run this on the VPS after MediaWiki is set up.

Imports ALL pages including character pages. Only User:/Talk: namespaces are skipped.

Usage:
    python3 import-content.py --full      # Full import of all pages
    python3 import-content.py --recent    # Import recent changes only
    python3 import-content.py --templates # Templates, categories, MediaWiki pages only
    python3 import-content.py --images    # Import images
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

# Configuration
SOURCE_WIKI = "https://gswiki.play.net"
SOURCE_API = f"{SOURCE_WIKI}/api.php"
LOCAL_WIKI_DIR = "/var/www/gswiki-archive"
LOCAL_SETTINGS = f"{LOCAL_WIKI_DIR}/LocalSettings.php"
DELAY_SECONDS = 2  # Be polite to source wiki
BATCH_SIZE = 50    # Pages per export batch


def disable_read_only():
    """Temporarily disable read-only mode for import."""
    print("Disabling read-only mode for import...")
    try:
        with open(LOCAL_SETTINGS, 'r') as f:
            content = f.read()

        # Comment out the $wgReadOnly line
        new_content = content.replace('$wgReadOnly =', '# $wgReadOnly =')

        with open(LOCAL_SETTINGS, 'w') as f:
            f.write(new_content)
        return True
    except Exception as e:
        print(f"  Warning: Could not disable read-only: {e}")
        return False


def enable_read_only():
    """Re-enable read-only mode after import."""
    print("Re-enabling read-only mode...")
    try:
        with open(LOCAL_SETTINGS, 'r') as f:
            content = f.read()

        # Uncomment the $wgReadOnly line
        new_content = content.replace('# $wgReadOnly =', '$wgReadOnly =')

        with open(LOCAL_SETTINGS, 'w') as f:
            f.write(new_content)
        return True
    except Exception as e:
        print(f"  Warning: Could not re-enable read-only: {e}")
        return False

# Namespaces to skip (User/Talk pages only - we want ALL content including character pages)
SKIP_NAMESPACES = ["User:", "User_talk:", "Talk:"]

def api_request(params, description="API request"):
    """Make an API request to source wiki."""
    params["format"] = "json"

    for attempt in range(3):
        try:
            time.sleep(DELAY_SECONDS)
            response = requests.get(SOURCE_API, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"  Attempt {attempt + 1}/3 failed for {description}: {e}")
            if attempt < 2:
                time.sleep(5)
    return None


def get_all_pages():
    """Get list of all pages from source wiki."""
    print("Fetching page list from source wiki...")
    pages = []

    # Namespaces to import:
    # 0 = Main, 4 = Project, 6 = File, 8 = MediaWiki, 10 = Template, 14 = Category
    namespaces_to_import = ["0", "4", "6", "8", "10", "14"]

    for ns in namespaces_to_import:
        print(f"  Fetching namespace {ns}...")
        params = {
            "action": "query",
            "list": "allpages",
            "aplimit": "500",
            "apfilterredir": "nonredirects",
            "apnamespace": ns,
        }

        while True:
            data = api_request(params.copy(), "fetching page list")
            if not data:
                break

            batch = data.get("query", {}).get("allpages", [])
            pages.extend([p["title"] for p in batch])
            print(f"  Retrieved {len(pages)} pages...")

            if "continue" in data:
                params["apcontinue"] = data["continue"]["apcontinue"]
            else:
                break

    return pages


def should_skip_page(title):
    """Check if a page should be skipped (User/Talk namespaces only)."""
    for ns in SKIP_NAMESPACES:
        if title.startswith(ns):
            return True
    return False


def export_pages(titles):
    """Export pages from source wiki as XML."""
    print(f"  Exporting batch of {len(titles)} pages...")

    params = {
        "action": "query",
        "titles": "|".join(titles),
        "export": "1",
        "exportnowrap": "1",
    }

    time.sleep(DELAY_SECONDS)
    response = requests.get(SOURCE_API, params=params, timeout=60)
    response.raise_for_status()

    return response.text


def import_xml(xml_content):
    """Import XML content into local MediaWiki."""
    # Write XML to temp file
    tmp_file = "/tmp/gswiki-import.xml"
    with open(tmp_file, "w", encoding="utf-8") as f:
        f.write(xml_content)

    # Run MediaWiki import script
    result = subprocess.run(
        ["php", f"{LOCAL_WIKI_DIR}/maintenance/importDump.php", tmp_file],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"    Import error: {result.stderr}")
        return False

    return True


def import_images():
    """Import images from source wiki."""
    print("\nFetching image list...")

    images = []
    params = {
        "action": "query",
        "list": "allimages",
        "ailimit": "500",
    }

    while True:
        data = api_request(params.copy(), "fetching image list")
        if not data:
            break

        batch = data.get("query", {}).get("allimages", [])
        images.extend(batch)
        print(f"  Retrieved {len(images)} images...")

        if "continue" in data:
            params["aicontinue"] = data["continue"]["aicontinue"]
        else:
            break

    print(f"Total images: {len(images)}")

    # Download images
    img_dir = Path(LOCAL_WIKI_DIR) / "images" / "imported"
    img_dir.mkdir(parents=True, exist_ok=True)

    for i, img in enumerate(images):
        name = img["name"]
        url = img["url"]

        print(f"  [{i+1}/{len(images)}] Downloading: {name}")

        try:
            time.sleep(DELAY_SECONDS)
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            filepath = img_dir / name
            with open(filepath, "wb") as f:
                f.write(response.content)

        except Exception as e:
            print(f"    Failed: {e}")

    # Import via maintenance script
    print("\nImporting images into MediaWiki...")
    result = subprocess.run(
        ["php", f"{LOCAL_WIKI_DIR}/maintenance/importImages.php", str(img_dir)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"  Import error: {result.stderr}")
    else:
        print("  Images imported successfully")


def full_import():
    """Perform full import of all pages (including character pages)."""
    print("\n=== FULL IMPORT ===\n")

    # Get all pages
    all_pages = get_all_pages()

    # Filter only User/Talk namespaces
    pages_to_import = [p for p in all_pages if not should_skip_page(p)]
    print(f"\nPages to import: {len(pages_to_import)}")

    # Import in batches
    total_batches = (len(pages_to_import) + BATCH_SIZE - 1) // BATCH_SIZE
    imported = 0
    failed = 0

    for i in range(0, len(pages_to_import), BATCH_SIZE):
        batch = pages_to_import[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1

        print(f"\n[Batch {batch_num}/{total_batches}]")

        try:
            xml = export_pages(batch)
            if import_xml(xml):
                imported += len(batch)
                print(f"  Imported {len(batch)} pages")
            else:
                failed += len(batch)
        except Exception as e:
            print(f"  Batch failed: {e}")
            failed += len(batch)

    print(f"\n=== IMPORT COMPLETE ===")
    print(f"Imported: {imported}")
    print(f"Failed: {failed}")

    # Rebuild search index
    print("\nRebuilding search index...")
    subprocess.run(["php", f"{LOCAL_WIKI_DIR}/maintenance/rebuildtextindex.php"])

    # Update page links
    print("Refreshing links...")
    subprocess.run(["php", f"{LOCAL_WIKI_DIR}/maintenance/refreshLinks.php"])


def templates_import():
    """Import only templates, MediaWiki pages, and categories (not main articles)."""
    print("\n=== IMPORTING TEMPLATES & MEDIAWIKI PAGES ===\n")

    pages = []
    # Only non-article namespaces: 4=Project, 6=File, 8=MediaWiki, 10=Template, 14=Category
    namespaces = ["4", "6", "8", "10", "14"]

    for ns in namespaces:
        print(f"  Fetching namespace {ns}...")
        params = {
            "action": "query",
            "list": "allpages",
            "aplimit": "500",
            "apfilterredir": "nonredirects",
            "apnamespace": ns,
        }

        while True:
            data = api_request(params.copy(), f"fetching namespace {ns}")
            if not data:
                break

            batch = data.get("query", {}).get("allpages", [])
            pages.extend([p["title"] for p in batch])
            print(f"  Retrieved {len(pages)} pages...")

            if "continue" in data:
                params["apcontinue"] = data["continue"]["apcontinue"]
            else:
                break

    print(f"\nPages to import: {len(pages)}")

    # Import in batches
    total_batches = (len(pages) + BATCH_SIZE - 1) // BATCH_SIZE
    imported = 0
    failed = 0

    for i in range(0, len(pages), BATCH_SIZE):
        batch = pages[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1

        print(f"\n[Batch {batch_num}/{total_batches}]")

        try:
            xml = export_pages(batch)
            if import_xml(xml):
                imported += len(batch)
                print(f"  Imported {len(batch)} pages")
            else:
                failed += len(batch)
        except Exception as e:
            print(f"  Batch failed: {e}")
            failed += len(batch)

    print(f"\n=== IMPORT COMPLETE ===")
    print(f"Imported: {imported}")
    print(f"Failed: {failed}")


def recent_import(days=7):
    """Import only recently changed pages."""
    print(f"\n=== IMPORTING RECENT CHANGES ({days} days) ===\n")

    # Get recent changes
    params = {
        "action": "query",
        "list": "recentchanges",
        "rclimit": "500",
        "rcprop": "title",
        "rctype": "edit|new",
    }

    data = api_request(params, "fetching recent changes")
    if not data:
        print("Failed to fetch recent changes")
        return

    changes = data.get("query", {}).get("recentchanges", [])
    titles = list(set(c["title"] for c in changes))

    # Filter only User/Talk namespaces
    titles = [t for t in titles if not should_skip_page(t)]

    print(f"Recent pages to import: {len(titles)}")

    if not titles:
        print("No changes to import")
        return

    # Import
    for i in range(0, len(titles), BATCH_SIZE):
        batch = titles[i:i + BATCH_SIZE]
        print(f"\nImporting batch of {len(batch)} pages...")

        try:
            xml = export_pages(batch)
            import_xml(xml)
        except Exception as e:
            print(f"  Failed: {e}")

    print("\n=== IMPORT COMPLETE ===")


def main():
    parser = argparse.ArgumentParser(description="Import GSWiki content")
    parser.add_argument("--full", action="store_true", help="Full import of all pages")
    parser.add_argument("--recent", action="store_true", help="Import recent changes only")
    parser.add_argument("--images", action="store_true", help="Import images")
    parser.add_argument("--templates", action="store_true", help="Import only templates, MediaWiki pages, categories (fast)")
    args = parser.parse_args()

    if not any([args.full, args.recent, args.images, args.templates]):
        parser.print_help()
        sys.exit(1)

    print("GSWiki Archive - Content Import")
    print("=" * 50)

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
    finally:
        # Always re-enable read-only mode, even if import fails
        enable_read_only()


if __name__ == "__main__":
    main()
