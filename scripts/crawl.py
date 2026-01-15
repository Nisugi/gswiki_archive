#!/usr/bin/env python3
"""
Wiki Archive Crawler

A polite, incremental crawler for archiving the wiki (all namespaces, including user/talk).
Respects the wiki by using appropriate delays and identifying itself.

Usage:
    python scripts/crawl.py --incremental  # Crawl only changed pages (default)
    python scripts/crawl.py --full         # Full crawl of entire wiki
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, quote

import requests
from bs4 import BeautifulSoup

# Add project root to path for shared lib
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.wiki_api import WikiAPI
from lib.logging_config import setup_logging
from lib.filename_utils import title_to_filename, filename_to_title

# Load config
CONFIG_PATH = PROJECT_ROOT / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

# Paths (configurable via config.json)
DOCS_DIR = PROJECT_ROOT / CONFIG["output"]["docs_dir"]
WIKI_DIR = PROJECT_ROOT / CONFIG["output"]["wiki_dir"]
DATA_DIR = PROJECT_ROOT / CONFIG["output"]["data_dir"]
MANIFEST_PATH = DATA_DIR / "manifest.json"

# Wiki settings
WIKI_NAME = CONFIG["wiki"]["name"]
BASE_URL = CONFIG["wiki"]["base_url"]
API_URL = CONFIG["wiki"]["api_endpoint"]
LIVE_WIKI_URL = CONFIG["wiki"]["live_wiki_url"]
USER_AGENT = CONFIG["crawl"]["user_agent"]
DELAY = CONFIG["crawl"]["delay_seconds"]
TIMEOUT = CONFIG["crawl"]["timeout_seconds"]
MAX_RETRIES = CONFIG["crawl"]["max_retries"]
RETRY_DELAY = CONFIG["crawl"]["retry_delay_seconds"]

# Set up logging (logs to ./logs by default)
logger = setup_logging(
    name="crawl",
    wiki_id=CONFIG["wiki"]["name"].lower().replace(" ", "-"),
    log_dir=str(PROJECT_ROOT / "logs"),
)

# Set up API client
api = WikiAPI(
    api_url=API_URL,
    wiki_name=WIKI_NAME,
    delay=DELAY,
    timeout=TIMEOUT,
    max_retries=MAX_RETRIES,
    retry_delay=RETRY_DELAY,
    user_agent=USER_AGENT,
    logger=logger,
)


def load_manifest() -> dict:
    """Load the existing manifest of crawled pages."""
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"pages": {}, "last_crawl": None, "version": 1}


def save_manifest(manifest: dict):
    """Save the manifest."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def fetch_page_html(title: str) -> str | None:
    """Fetch the HTML content of a wiki page."""
    url = f"{BASE_URL}/{quote(title.replace(' ', '_'))}"

    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(DELAY)
            response = api.session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed for {title}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)

    return None


def rewrite_internal_links(soup: BeautifulSoup, base_url: str):
    """Rewrite internal wiki links to point to our archive."""
    for a in soup.find_all("a", href=True):
        href = a["href"]

        # Skip external links, anchors, and special URLs
        if href.startswith(("http://", "https://", "mailto:", "#", "javascript:")):
            # Check if it's a link to the wiki itself
            if href.startswith(base_url + "/"):
                path = href[len(base_url) + 1:]
                if not path.startswith(("Special:", "api.php")):
                    filename = title_to_filename(path.replace("_", " "))
                    a["href"] = f"/wiki/{filename}"
            continue

        # Handle relative links
        if href.startswith("/"):
            path = href[1:]

            # Skip special pages and API
            if path.startswith(("Special:", "api.php", "index.php")):
                a["href"] = base_url + href
                continue

            # Convert to archive link
            title = path.replace("_", " ")
            filename = title_to_filename(title)
            a["href"] = f"/wiki/{filename}"


def make_images_absolute(soup: BeautifulSoup, base_url: str):
    """Make image sources absolute and add fallback handling."""
    for img in soup.find_all("img", src=True):
        src = img["src"]

        if src.startswith("/"):
            img["src"] = base_url + src
        elif not src.startswith(("http://", "https://", "data:")):
            img["src"] = urljoin(base_url, src)

        img["onerror"] = "this.classList.add('archive-img-unavailable'); this.onerror=null;"

        if not img.get("width") and not img.get("style"):
            img["class"] = img.get("class", []) + ["archive-img"]


def make_resources_absolute(soup: BeautifulSoup, base_url: str):
    """Make CSS and JS resource URLs absolute so they load from the original wiki."""
    for link in soup.find_all("link", href=True):
        href = link["href"]
        if href.startswith("/") and not href.startswith("//"):
            link["href"] = base_url + href

    for script in soup.find_all("script", src=True):
        src = script["src"]
        if src.startswith("/") and not src.startswith("//"):
            script["src"] = base_url + src


def inject_archive_banner(soup: BeautifulSoup, crawl_timestamp: str):
    """Inject the archive banner at the top of the page."""
    banner_html = f'''
    <div id="archive-banner">
        <div class="archive-banner-content">
            <span class="archive-icon">&#128230;</span>
            <span class="archive-text">
                <strong>ARCHIVED SNAPSHOT</strong> of {WIKI_NAME} &bull;
                Captured: {crawl_timestamp} UTC
            </span>
            <a href="{LIVE_WIKI_URL}" class="archive-live-link" target="_blank" rel="noopener">
                View live wiki &rarr;
            </a>
        </div>
    </div>
    '''

    banner = BeautifulSoup(banner_html, "html.parser")

    head = soup.find("head")
    if head:
        css_link = soup.new_tag("link", rel="stylesheet", href="/assets/archive.css")
        head.append(css_link)
        js_link = soup.new_tag("script", src="/assets/archive.js")
        head.append(js_link)

    body = soup.find("body")
    if body:
        body.insert(0, banner)


def process_page(title: str, crawl_timestamp: str) -> str | None:
    """Fetch and process a single page."""
    html = fetch_page_html(title)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    rewrite_internal_links(soup, BASE_URL)
    make_images_absolute(soup, BASE_URL)
    make_resources_absolute(soup, BASE_URL)
    inject_archive_banner(soup, crawl_timestamp)

    return str(soup)


def crawl_full():
    """Perform a full crawl of the wiki."""
    logger.info("=== FULL CRAWL ===")
    crawl_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    all_pages = api.get_all_pages()
    manifest = {"pages": {}, "last_crawl": crawl_timestamp, "version": 1}

    WIKI_DIR.mkdir(parents=True, exist_ok=True)

    total = len(all_pages)
    processed = 0
    failed = 0

    for i, page in enumerate(all_pages):
        title = page["title"]
        logger.info(f"[{i+1}/{total}] Processing: {title}")

        html = process_page(title, crawl_timestamp)
        if html:
            filename = title_to_filename(title)
            filepath = WIKI_DIR / filename
            filepath.write_text(html, encoding="utf-8")

            manifest["pages"][title] = {
                "filename": filename,
                "crawled": crawl_timestamp,
            }
            processed += 1
        else:
            logger.error(f"FAILED to fetch: {title}")
            failed += 1

    save_manifest(manifest)
    logger.info(f"=== CRAWL COMPLETE === Processed: {processed}, Failed: {failed}")
    return manifest


def crawl_incremental():
    """Perform an incremental crawl based on recent changes."""
    logger.info("=== INCREMENTAL CRAWL ===")

    manifest = load_manifest()
    last_crawl = manifest.get("last_crawl")

    if not last_crawl:
        logger.info("No previous crawl found. Running full crawl instead.")
        return crawl_full()

    crawl_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    # Convert last_crawl to API format
    last_crawl_dt = datetime.strptime(last_crawl, "%Y-%m-%d %H:%M")
    last_crawl_api = last_crawl_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    changed_pages = api.get_recent_changes(last_crawl_api)

    if not changed_pages:
        logger.info("No changes since last crawl.")
        return manifest

    WIKI_DIR.mkdir(parents=True, exist_ok=True)

    processed = 0
    failed = 0

    for title in changed_pages:
        logger.info(f"Processing: {title}")

        html = process_page(title, crawl_timestamp)
        if html:
            filename = title_to_filename(title)
            filepath = WIKI_DIR / filename
            filepath.write_text(html, encoding="utf-8")

            manifest["pages"][title] = {
                "filename": filename,
                "crawled": crawl_timestamp,
            }
            processed += 1
        else:
            logger.error(f"FAILED to fetch: {title}")
            failed += 1

    manifest["last_crawl"] = crawl_timestamp
    save_manifest(manifest)

    logger.info(f"=== CRAWL COMPLETE === Processed: {processed}, Failed: {failed}")
    return manifest


def main():
    """Main entry point."""
    logger.info(f"{WIKI_NAME} Archive Crawler")
    logger.info("=" * 50)
    logger.info(f"User-Agent: {USER_AGENT}")
    logger.info(f"Delay: {DELAY} seconds between requests")

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

    if mode == "full":
        crawl_full()
    else:
        crawl_incremental()


if __name__ == "__main__":
    main()
