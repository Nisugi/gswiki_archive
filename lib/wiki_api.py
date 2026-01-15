#!/usr/bin/env python3
"""
Shared Wiki API client for wiki archive scripts.

Provides common functionality for interacting with MediaWiki APIs:
- Rate-limited requests with retries
- Namespace enumeration
- Page listing with pagination
- Proper logging

Usage:
    from lib.wiki_api import WikiAPI

    api = WikiAPI(
        api_url="https://gswiki.play.net/api.php",
        wiki_name="GSWiki",
        delay=2,
    )
    pages = api.get_all_pages()
"""

import logging
import time
from typing import Optional

import requests


class WikiAPI:
    """MediaWiki API client with rate limiting and retries."""

    def __init__(
        self,
        api_url: str,
        wiki_name: str = "Wiki",
        delay: float = 2.0,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        user_agent: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the Wiki API client.

        Args:
            api_url: MediaWiki API endpoint (e.g., https://wiki.example.com/api.php)
            wiki_name: Human-readable wiki name for logging
            delay: Seconds to wait between requests (be polite)
            timeout: Request timeout in seconds
            max_retries: Number of retry attempts for failed requests
            retry_delay: Seconds to wait between retries
            user_agent: Custom user agent string
            logger: Logger instance (creates one if not provided)
        """
        self.api_url = api_url
        self.wiki_name = wiki_name
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Set up logger
        self.logger = logger or logging.getLogger(f"wiki_api.{wiki_name}")

        # Set up session
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent or f"{wiki_name}-Archiver/1.0 (community preservation)",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.5",
        })

    def request(self, params: dict, description: str = "API request") -> Optional[dict]:
        """
        Make an API request with retries and rate limiting.

        Args:
            params: Query parameters for the API call
            description: Human-readable description for logging

        Returns:
            JSON response as dict, or None if all retries failed
        """
        params["format"] = "json"

        for attempt in range(self.max_retries):
            try:
                time.sleep(self.delay)  # Rate limiting
                response = self.session.get(
                    self.api_url,
                    params=params,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()

            except requests.RequestException as e:
                self.logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries} failed for {description}: {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)

        self.logger.error(f"FAILED after {self.max_retries} attempts: {description}")
        return None

    def get_namespaces(self) -> list[int]:
        """
        Fetch all non-negative namespace IDs from the wiki.

        Returns:
            Sorted list of namespace IDs (defaults to [0] on failure)
        """
        data = self.request(
            {"action": "query", "meta": "siteinfo", "siprop": "namespaces"},
            "fetching namespaces",
        )

        if not data:
            self.logger.warning("Failed to fetch namespaces; defaulting to main namespace only")
            return [0]

        namespaces = []
        for ns_id_str in data.get("query", {}).get("namespaces", {}):
            try:
                ns_id = int(ns_id_str)
                if ns_id >= 0:
                    namespaces.append(ns_id)
            except ValueError:
                continue

        self.logger.debug(f"Found {len(namespaces)} namespaces")
        return sorted(set(namespaces))

    def get_all_pages(self, namespaces: Optional[list[int]] = None) -> list[dict]:
        """
        Fetch list of all pages across specified namespaces.

        Args:
            namespaces: List of namespace IDs to query (None = all namespaces)

        Returns:
            List of page dicts with 'title' and 'pageid' keys
        """
        if namespaces is None:
            namespaces = self.get_namespaces()

        self.logger.info(f"Fetching pages from {len(namespaces)} namespaces...")
        pages = []

        for ns in namespaces:
            params = {
                "action": "query",
                "list": "allpages",
                "aplimit": "500",
                "apnamespace": str(ns),
            }

            while True:
                data = self.request(params.copy(), f"fetching page list (ns={ns})")
                if not data:
                    break

                batch = data.get("query", {}).get("allpages", [])
                pages.extend(batch)
                self.logger.debug(f"Retrieved {len(pages)} pages so far...")

                if "continue" in data:
                    params["apcontinue"] = data["continue"]["apcontinue"]
                else:
                    break

        self.logger.info(f"Total pages found: {len(pages)}")
        return pages

    def get_page_titles(self, namespaces: Optional[list[int]] = None) -> list[str]:
        """
        Fetch list of all page titles across specified namespaces.

        Args:
            namespaces: List of namespace IDs to query (None = all namespaces)

        Returns:
            List of page title strings
        """
        pages = self.get_all_pages(namespaces)
        return [p["title"] for p in pages]

    def get_recent_changes(self, since: str, types: str = "edit|new") -> set[str]:
        """
        Get pages changed since a given timestamp.

        Args:
            since: ISO timestamp (e.g., "2024-01-01T00:00:00Z")
            types: Change types to include (default: "edit|new")

        Returns:
            Set of page titles that have changed
        """
        from datetime import datetime, timezone

        self.logger.info(f"Fetching changes since {since}...")
        changed_pages = set()

        params = {
            "action": "query",
            "list": "recentchanges",
            "rcstart": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "rcend": since,
            "rclimit": "500",
            "rcprop": "title",
            "rctype": types,
        }

        while True:
            data = self.request(params.copy(), "fetching recent changes")
            if not data:
                break

            changes = data.get("query", {}).get("recentchanges", [])
            for change in changes:
                changed_pages.add(change["title"])

            if "continue" in data:
                params["rccontinue"] = data["continue"]["rccontinue"]
            else:
                break

        self.logger.info(f"Pages changed since last crawl: {len(changed_pages)}")
        return changed_pages

    def get_all_images(self) -> list[dict]:
        """
        Fetch list of all images from the wiki.

        Returns:
            List of image dicts with 'name' and 'url' keys
        """
        self.logger.info("Fetching image list...")
        images = []

        params = {
            "action": "query",
            "list": "allimages",
            "ailimit": "500",
        }

        while True:
            data = self.request(params.copy(), "fetching image list")
            if not data:
                break

            batch = data.get("query", {}).get("allimages", [])
            images.extend(batch)
            self.logger.debug(f"Retrieved {len(images)} images...")

            if "continue" in data:
                params["aicontinue"] = data["continue"]["aicontinue"]
            else:
                break

        self.logger.info(f"Total images found: {len(images)}")
        return images

    def export_pages(self, titles: list[str]) -> Optional[str]:
        """
        Export pages as XML using the MediaWiki export API.

        Args:
            titles: List of page titles to export

        Returns:
            XML content as string, or None on failure
        """
        self.logger.debug(f"Exporting batch of {len(titles)} pages...")

        params = {
            "action": "query",
            "titles": "|".join(titles),
            "export": "1",
            "exportnowrap": "1",
        }

        time.sleep(self.delay)
        try:
            response = self.session.get(self.api_url, params=params, timeout=60)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"Export failed: {e}")
            return None
