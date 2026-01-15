#!/usr/bin/env python3
"""
Wiki Static Mirror - Post-Processing Fix
Fixes CSS references and layout issues in wget-mirrored wiki pages.

Usage:
    python fix-static-mirror.py <mirror_directory> [--wiki-name NAME] [--live-url URL]

Examples:
    python fix-static-mirror.py ./gswiki-static-2026-01-15 --wiki-name "GSWiki" --live-url "https://gswiki.play.net"
    python fix-static-mirror.py ./elanthipedia-static-2026-01-15 --wiki-name "Elanthipedia" --live-url "https://elanthipedia.play.net"
"""

import argparse
import os
import re
import sys
from pathlib import Path

# Default values (can be overridden via command line)
DEFAULT_WIKI_NAME = "GSWiki"
DEFAULT_LIVE_URL = "https://gswiki.play.net"

# Minimal CSS to make the wiki look right offline
# Use WIKI_NAME_PLACEHOLDER which will be replaced at runtime
OFFLINE_CSS_TEMPLATE = """
<style>
/* WIKI_NAME_PLACEHOLDER Offline Mirror - Layout Fix */
body {
    margin: 0;
    padding: 0;
    font-family: sans-serif;
    background: #f6f6f6;
}

/* Main content area */
#content {
    margin: 0 0 0 10em;
    padding: 1em 1.5em;
    background: white;
    border: 1px solid #a7d7f9;
    border-right: none;
    min-height: 100vh;
}

/* Sidebar/Navigation panel */
#mw-panel, #mw-navigation {
    position: fixed;
    top: 0;
    left: 0;
    width: 10em;
    height: 100%;
    background: #f6f6f6;
    padding: 1em 0.5em;
    overflow-y: auto;
    font-size: 0.85em;
    z-index: 100;
}

#mw-panel .portal {
    margin-bottom: 1em;
}

#mw-panel .portal h3 {
    font-size: 0.9em;
    font-weight: bold;
    margin: 0 0 0.5em 0;
    padding: 0.25em;
    background: #e0e0e0;
}

#mw-panel .portal .body {
    padding-left: 0.5em;
}

#mw-panel .portal .body ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

#mw-panel .portal .body li {
    margin: 0.3em 0;
}

#mw-panel a {
    color: #0645ad;
    text-decoration: none;
}

#mw-panel a:hover {
    text-decoration: underline;
}

/* Header elements */
#mw-head, #mw-head-base, #mw-page-base {
    display: none;
}

#firstHeading {
    font-size: 1.8em;
    margin: 0 0 0.5em 0;
    padding-bottom: 0.2em;
    border-bottom: 1px solid #a7d7f9;
}

/* Hide edit/login stuff */
#ca-edit, #ca-viewsource, #ca-history, #ca-watch, #ca-unwatch,
#pt-login, #pt-createaccount, .mw-editsection,
#mw-head, .noprint {
    display: none !important;
}

/* Content styling */
#mw-content-text {
    line-height: 1.6;
}

#mw-content-text a {
    color: #0645ad;
}

#mw-content-text a:visited {
    color: #0b0080;
}

#mw-content-text a.new, #mw-content-text a.new:visited {
    color: #d33;
}

/* Tables */
table {
    border-collapse: collapse;
}

.wikitable {
    background: white;
    border: 1px solid #a2a9b1;
    margin: 1em 0;
}

.wikitable th, .wikitable td {
    border: 1px solid #a2a9b1;
    padding: 0.4em 0.6em;
}

.wikitable th {
    background: #eaecf0;
}

/* Info boxes */
.infobox {
    float: right;
    clear: right;
    margin: 0 0 1em 1em;
    padding: 0.5em;
    background: #f8f9fa;
    border: 1px solid #a2a9b1;
    font-size: 0.9em;
    width: 22em;
}

/* Table of contents */
#toc, .toc {
    background: #f8f9fa;
    border: 1px solid #a2a9b1;
    padding: 0.5em 1em;
    display: inline-block;
    margin: 1em 0;
}

/* Images */
.thumb {
    margin: 0.5em;
    background: #f8f9fa;
    border: 1px solid #c8ccd1;
    padding: 3px;
}

.thumbinner {
    padding: 3px;
}

.thumbcaption {
    font-size: 0.85em;
    padding: 3px;
}

/* Categories */
#catlinks {
    margin-top: 2em;
    padding: 0.5em;
    background: #f8f9fa;
    border: 1px solid #a2a9b1;
    font-size: 0.9em;
}

/* Footer */
#footer {
    margin-left: 10em;
    padding: 1em;
    background: #f6f6f6;
    border-top: 1px solid #a7d7f9;
    font-size: 0.8em;
    color: #555;
}

/* Responsive - collapse sidebar on small screens */
@media (max-width: 800px) {
    #mw-panel, #mw-navigation {
        position: relative;
        width: 100%;
        height: auto;
    }
    #content {
        margin-left: 0;
    }
    #footer {
        margin-left: 0;
    }
}

/* Archive banner */
#archive-notice {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: white;
    padding: 8px;
    text-align: center;
    font-size: 13px;
    z-index: 1000;
    border-bottom: 2px solid #e94560;
}

#archive-notice a {
    color: #7dd3fc;
    margin-left: 10px;
}

body.has-archive-notice {
    padding-top: 40px;
}

body.has-archive-notice #mw-panel {
    top: 40px;
}
</style>
"""

# Archive banner HTML template
# Uses WIKI_NAME_PLACEHOLDER and LIVE_URL_PLACEHOLDER which will be replaced at runtime
ARCHIVE_BANNER_TEMPLATE = """
<div id="archive-notice">
    <strong style="color: #e94560;">OFFLINE ARCHIVE</strong> -
    Static snapshot of WIKI_NAME_PLACEHOLDER for offline viewing
    <a href="LIVE_URL_PLACEHOLDER" target="_blank">View live wiki &rarr;</a>
</div>
<script>document.body.classList.add('has-archive-notice');</script>
"""


def get_offline_css(wiki_name):
    """Generate CSS with the wiki name."""
    return OFFLINE_CSS_TEMPLATE.replace("WIKI_NAME_PLACEHOLDER", wiki_name)


def get_archive_banner(wiki_name, live_url):
    """Generate archive banner with wiki name and live URL."""
    return ARCHIVE_BANNER_TEMPLATE.replace(
        "WIKI_NAME_PLACEHOLDER", wiki_name
    ).replace(
        "LIVE_URL_PLACEHOLDER", live_url
    )


def fix_html_file(filepath, wiki_name, live_url):
    """Fix CSS references and layout in a single HTML file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        return False

    original = content

    # Remove external CSS links (they don't work offline)
    content = re.sub(
        r'<link[^>]*href="[^"]*load\.php[^"]*"[^>]*/?>',
        '',
        content
    )

    # Remove external script references to load.php
    content = re.sub(
        r'<script[^>]*src="[^"]*load\.php[^"]*"[^>]*></script>',
        '',
        content
    )

    # Get CSS and banner with wiki-specific values
    offline_css = get_offline_css(wiki_name)
    archive_banner = get_archive_banner(wiki_name, live_url)

    # Inject our CSS after <head>
    if '<head>' in content:
        content = content.replace('<head>', '<head>' + offline_css, 1)
    elif '<HEAD>' in content:
        content = content.replace('<HEAD>', '<HEAD>' + offline_css, 1)

    # Add archive banner after <body...>
    content = re.sub(
        r'(<body[^>]*>)',
        r'\1' + archive_banner,
        content,
        count=1
    )

    # Fix internal links - convert /PageName to PageName.html
    # But only for links that look like wiki pages (not external, not anchors)
    def fix_link(match):
        href = match.group(1)
        # Skip external links, anchors, and already-fixed links
        if href.startswith('http') or href.startswith('#') or href.endswith('.html'):
            return match.group(0)
        if href.startswith('/'):
            # Convert /Page_Name to Page_Name.html
            page = href[1:]  # Remove leading /
            if '?' not in page and '.' not in page:
                return f'href="{page}.html"'
        return match.group(0)

    content = re.sub(r'href="([^"]*)"', fix_link, content)

    # Only write if changed
    if content != original:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"  Error writing {filepath}: {e}")
            return False

    return False


def main():
    parser = argparse.ArgumentParser(
        description="Fix CSS references and layout in wget-mirrored wiki pages"
    )
    parser.add_argument(
        "mirror_directory",
        help="Path to the mirror directory containing HTML files"
    )
    parser.add_argument(
        "--wiki-name",
        default=DEFAULT_WIKI_NAME,
        help=f"Name of the wiki (default: {DEFAULT_WIKI_NAME})"
    )
    parser.add_argument(
        "--live-url",
        default=DEFAULT_LIVE_URL,
        help=f"URL of the live wiki (default: {DEFAULT_LIVE_URL})"
    )
    args = parser.parse_args()

    mirror_dir = Path(args.mirror_directory)
    wiki_name = args.wiki_name
    live_url = args.live_url

    if not mirror_dir.exists():
        print(f"Error: Directory '{mirror_dir}' does not exist")
        sys.exit(1)

    print(f"Fixing static mirror in: {mirror_dir}")
    print(f"  Wiki name: {wiki_name}")
    print(f"  Live URL: {live_url}")
    print()

    # Find all HTML files
    html_files = list(mirror_dir.glob("**/*.html"))
    print(f"Found {len(html_files)} HTML files")

    fixed = 0
    for i, filepath in enumerate(html_files):
        if fix_html_file(filepath, wiki_name, live_url):
            fixed += 1

        # Progress indicator
        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(html_files)} files...")

    print()
    print(f"Done! Fixed {fixed} files.")
    print()
    print("To view the archive:")
    print(f"  Open {mirror_dir / 'Main_Page.html'} in your browser")


if __name__ == "__main__":
    main()
