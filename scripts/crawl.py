#!/usr/bin/env python3
"""
GSWiki Archive Crawler

A polite, incremental crawler for archiving GSWiki.
Respects the wiki by using appropriate delays and identifying itself.
"""

import json
import os
import re
import sys
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, quote

import requests
from bs4 import BeautifulSoup

# Load config
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

# Paths
DOCS_DIR = PROJECT_ROOT / CONFIG["output"]["docs_dir"]
WIKI_DIR = PROJECT_ROOT / CONFIG["output"]["wiki_dir"]
ASSETS_DIR = PROJECT_ROOT / CONFIG["output"]["assets_dir"]
DATA_DIR = PROJECT_ROOT / CONFIG["output"]["data_dir"]
MANIFEST_PATH = DATA_DIR / "manifest.json"
EXCLUSIONS_PATH = DATA_DIR / "exclusions.json"
OPTED_IN_PATH = PROJECT_ROOT / CONFIG["exclusions"]["opted_in_file"]

# Wiki settings
BASE_URL = CONFIG["wiki"]["base_url"]
API_URL = CONFIG["wiki"]["api_endpoint"]
USER_AGENT = CONFIG["crawl"]["user_agent"]
DELAY = CONFIG["crawl"]["delay_seconds"]
TIMEOUT = CONFIG["crawl"]["timeout_seconds"]
MAX_RETRIES = CONFIG["crawl"]["max_retries"]
RETRY_DELAY = CONFIG["crawl"]["retry_delay_seconds"]


def create_session():
    """Create a requests session with proper headers."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })
    return session


def api_request(session, params, description="API request"):
    """Make an API request with retries and politeness delay."""
    params["format"] = "json"

    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(DELAY)  # Be polite
            response = session.get(API_URL, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"  Attempt {attempt + 1}/{MAX_RETRIES} failed for {description}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)

    print(f"  FAILED: {description}")
    return None


def get_all_pages(session):
    """Fetch list of all pages from the wiki API."""
    print("Fetching list of all pages...")
    pages = []
    params = {
        "action": "query",
        "list": "allpages",
        "aplimit": "500",
        "apfilterredir": "nonredirects",  # Skip redirects
    }

    while True:
        data = api_request(session, params.copy(), "fetching page list")
        if not data:
            break

        batch = data.get("query", {}).get("allpages", [])
        pages.extend(batch)
        print(f"  Retrieved {len(pages)} pages so far...")

        # Check for continuation
        if "continue" in data:
            params["apcontinue"] = data["continue"]["apcontinue"]
        else:
            break

    print(f"Total pages found: {len(pages)}")
    return pages


def get_character_pages(session):
    """Fetch list of pages using characterprofile template (to exclude)."""
    print("Fetching character pages to exclude...")
    char_pages = set()

    for template in CONFIG["exclusions"]["templates"]:
        params = {
            "action": "query",
            "list": "embeddedin",
            "eititle": template,
            "eilimit": "500",
        }

        while True:
            data = api_request(session, params.copy(), f"fetching {template} users")
            if not data:
                break

            batch = data.get("query", {}).get("embeddedin", [])
            for page in batch:
                char_pages.add(page["title"])

            if "continue" in data:
                params["eicontinue"] = data["continue"]["eicontinue"]
            else:
                break

    print(f"Character pages to exclude: {len(char_pages)}")
    return char_pages


def get_opted_in_pages():
    """Load list of character pages that have opted into the archive."""
    if OPTED_IN_PATH.exists():
        with open(OPTED_IN_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def load_manifest():
    """Load the existing manifest of crawled pages."""
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"pages": {}, "last_crawl": None, "version": 1}


def save_manifest(manifest):
    """Save the manifest."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def save_exclusions(char_pages):
    """Save the exclusions list."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(EXCLUSIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(list(char_pages)), f, indent=2, ensure_ascii=False)


def title_to_filename(title):
    """Convert a wiki page title to a safe filename."""
    # Replace characters that are problematic in filenames
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


def filename_to_title(filename):
    """Convert a filename back to a wiki page title."""
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


def fetch_page_html(session, title):
    """Fetch the HTML content of a wiki page."""
    url = f"{BASE_URL}/{quote(title.replace(' ', '_'))}"

    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(DELAY)  # Be polite
            response = session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"    Attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)

    return None


def get_page_revision(session, title):
    """Get the latest revision ID for a page."""
    params = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "ids",
    }
    data = api_request(session, params, f"getting revision for {title}")
    if data:
        pages = data.get("query", {}).get("pages", {})
        for page_id, page_data in pages.items():
            if page_id != "-1":
                revisions = page_data.get("revisions", [])
                if revisions:
                    return revisions[0].get("revid")
    return None


def rewrite_internal_links(soup, base_url):
    """Rewrite internal wiki links to point to our archive."""
    for a in soup.find_all("a", href=True):
        href = a["href"]

        # Skip external links, anchors, and special URLs
        if href.startswith(("http://", "https://", "mailto:", "#", "javascript:")):
            # Check if it's a link to the wiki itself
            if href.startswith(base_url + "/"):
                # Convert to relative archive link
                path = href[len(base_url) + 1:]
                if not path.startswith(("Special:", "api.php")):
                    filename = title_to_filename(path.replace("_", " "))
                    a["href"] = f"/wiki/{filename}"
            continue

        # Handle relative links
        if href.startswith("/"):
            path = href[1:]  # Remove leading slash

            # Skip special pages and API
            if path.startswith(("Special:", "api.php", "index.php")):
                a["href"] = base_url + href  # Make absolute to live wiki
                continue

            # Convert to archive link
            title = path.replace("_", " ")
            filename = title_to_filename(title)
            a["href"] = f"/wiki/{filename}"


def make_images_absolute(soup, base_url):
    """Make image sources absolute and add fallback handling."""
    for img in soup.find_all("img", src=True):
        src = img["src"]

        # Make relative URLs absolute
        if src.startswith("/"):
            img["src"] = base_url + src
        elif not src.startswith(("http://", "https://", "data:")):
            img["src"] = urljoin(base_url, src)

        # Add error handler for fallback
        img["onerror"] = "this.classList.add('archive-img-unavailable'); this.onerror=null;"

        # Ensure width/height are preserved for layout
        if not img.get("width") and not img.get("style"):
            img["class"] = img.get("class", []) + ["archive-img"]


def make_resources_absolute(soup, base_url):
    """Make CSS and JS resource URLs absolute so they load from the original wiki."""
    # Fix stylesheet links
    for link in soup.find_all("link", href=True):
        href = link["href"]
        if href.startswith("/") and not href.startswith("//"):
            link["href"] = base_url + href

    # Fix script sources
    for script in soup.find_all("script", src=True):
        src = script["src"]
        if src.startswith("/") and not src.startswith("//"):
            script["src"] = base_url + src


def inject_archive_banner(soup, crawl_timestamp):
    """Inject the archive banner at the top of the page."""
    banner_html = f'''
    <div id="archive-banner">
        <div class="archive-banner-content">
            <span class="archive-icon">&#128230;</span>
            <span class="archive-text">
                <strong>ARCHIVED SNAPSHOT</strong> of GSWiki &bull;
                Captured: {crawl_timestamp} UTC
            </span>
            <a href="{CONFIG["wiki"]["live_wiki_url"]}" class="archive-live-link" target="_blank" rel="noopener">
                View live wiki &rarr;
            </a>
        </div>
    </div>
    '''

    banner = BeautifulSoup(banner_html, "html.parser")

    # Inject CSS and JS links in head
    head = soup.find("head")
    if head:
        css_link = soup.new_tag("link", rel="stylesheet", href="/assets/archive.css")
        head.append(css_link)

        js_link = soup.new_tag("script", src="/assets/archive.js")
        head.append(js_link)

    # Inject banner at start of body
    body = soup.find("body")
    if body:
        body.insert(0, banner)


def process_page(session, title, crawl_timestamp):
    """Fetch and process a single page."""
    html = fetch_page_html(session, title)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Rewrite links to stay in archive
    rewrite_internal_links(soup, BASE_URL)

    # Make images absolute with fallback
    make_images_absolute(soup, BASE_URL)

    # Make CSS/JS load from original wiki
    make_resources_absolute(soup, BASE_URL)

    # Inject archive banner
    inject_archive_banner(soup, crawl_timestamp)

    return str(soup)


def get_recent_changes(session, since_timestamp):
    """Get pages changed since the last crawl."""
    print(f"Fetching changes since {since_timestamp}...")
    changed_pages = set()

    params = {
        "action": "query",
        "list": "recentchanges",
        "rcstart": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rcend": since_timestamp,
        "rclimit": "500",
        "rcprop": "title",
        "rctype": "edit|new",
    }

    while True:
        data = api_request(session, params.copy(), "fetching recent changes")
        if not data:
            break

        changes = data.get("query", {}).get("recentchanges", [])
        for change in changes:
            changed_pages.add(change["title"])

        if "continue" in data:
            params["rccontinue"] = data["continue"]["rccontinue"]
        else:
            break

    print(f"Pages changed since last crawl: {len(changed_pages)}")
    return changed_pages


def should_skip_page(title, char_pages, opted_in):
    """Determine if a page should be skipped."""
    # Skip namespaces we don't want
    for ns in CONFIG["exclusions"]["namespaces_to_skip"]:
        if title.startswith(ns):
            return True

    # Skip character pages unless opted in
    if title in char_pages and title not in opted_in:
        return True

    return False


def crawl_full(session):
    """Perform a full crawl of the wiki."""
    print("\n=== FULL CRAWL ===\n")
    crawl_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    # Get all pages
    all_pages = get_all_pages(session)

    # Get exclusions
    char_pages = get_character_pages(session)
    save_exclusions(char_pages)
    opted_in = get_opted_in_pages()

    # Prepare manifest
    manifest = {"pages": {}, "last_crawl": crawl_timestamp, "version": 1}

    # Ensure output directory exists
    WIKI_DIR.mkdir(parents=True, exist_ok=True)

    # Process each page
    total = len(all_pages)
    processed = 0
    skipped = 0
    failed = 0

    for i, page in enumerate(all_pages):
        title = page["title"]

        if should_skip_page(title, char_pages, opted_in):
            skipped += 1
            continue

        print(f"[{i+1}/{total}] Processing: {title}")

        html = process_page(session, title, crawl_timestamp)
        if html:
            filename = title_to_filename(title)
            filepath = WIKI_DIR / filename
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html)

            manifest["pages"][title] = {
                "filename": filename,
                "crawled": crawl_timestamp,
            }
            processed += 1
        else:
            print(f"  FAILED to fetch: {title}")
            failed += 1

    save_manifest(manifest)

    print(f"\n=== CRAWL COMPLETE ===")
    print(f"Processed: {processed}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")

    return manifest


def crawl_incremental(session):
    """Perform an incremental crawl based on recent changes."""
    print("\n=== INCREMENTAL CRAWL ===\n")

    manifest = load_manifest()
    last_crawl = manifest.get("last_crawl")

    if not last_crawl:
        print("No previous crawl found. Running full crawl instead.")
        return crawl_full(session)

    crawl_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    # Convert last_crawl to API format
    last_crawl_dt = datetime.strptime(last_crawl, "%Y-%m-%d %H:%M")
    last_crawl_api = last_crawl_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Get changed pages
    changed_pages = get_recent_changes(session, last_crawl_api)

    if not changed_pages:
        print("No changes since last crawl.")
        return manifest

    # Get exclusions
    char_pages = get_character_pages(session)
    save_exclusions(char_pages)
    opted_in = get_opted_in_pages()

    # Process changed pages
    WIKI_DIR.mkdir(parents=True, exist_ok=True)

    processed = 0
    skipped = 0
    failed = 0

    for title in changed_pages:
        if should_skip_page(title, char_pages, opted_in):
            skipped += 1
            continue

        print(f"Processing: {title}")

        html = process_page(session, title, crawl_timestamp)
        if html:
            filename = title_to_filename(title)
            filepath = WIKI_DIR / filename
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html)

            manifest["pages"][title] = {
                "filename": filename,
                "crawled": crawl_timestamp,
            }
            processed += 1
        else:
            print(f"  FAILED to fetch: {title}")
            failed += 1

    manifest["last_crawl"] = crawl_timestamp
    save_manifest(manifest)

    print(f"\n=== CRAWL COMPLETE ===")
    print(f"Processed: {processed}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")

    return manifest


def main():
    """Main entry point."""
    print("GSWiki Archive Crawler")
    print("=" * 50)
    print(f"User-Agent: {USER_AGENT}")
    print(f"Delay: {DELAY} seconds between requests")
    print()

    # Parse command line
    mode = "incremental"
    if len(sys.argv) > 1:
        if sys.argv[1] in ("--full", "-f"):
            mode = "full"
        elif sys.argv[1] in ("--incremental", "-i"):
            mode = "incremental"
        elif sys.argv[1] in ("--help", "-h"):
            print("Usage: crawl.py [--full | --incremental]")
            print("  --full, -f        Perform full crawl of entire wiki")
            print("  --incremental, -i Crawl only pages changed since last run (default)")
            sys.exit(0)

    session = create_session()

    if mode == "full":
        crawl_full(session)
    else:
        crawl_incremental(session)


if __name__ == "__main__":
    main()
