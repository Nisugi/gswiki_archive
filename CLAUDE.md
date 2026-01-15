# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wiki archive system for game wikis (GSWiki/GemStone IV, Elanthipedia/DragonRealms). Provides three archive methods:
1. **MediaWiki on VPS** (primary) - Full MediaWiki installation with imported content
2. **Static HTML download** - Offline archive via wget crawl
3. **GitHub Pages** (legacy) - Static HTML with Pagefind search

## Common Commands

### GitHub Pages (scripts/)
```bash
# Install dependencies
pip install -r scripts/requirements.txt

# Run crawler (incremental by default)
python scripts/crawl.py --incremental
python scripts/crawl.py --full

# Build search index (requires pagefind: npm install -g pagefind)
python scripts/build_search.py
```

### Running Tests
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_filename_utils.py

# Run with verbose output
pytest tests/ -v
```

### VPS Server Scripts (server/)
All server scripts require sourcing a config file first (VPS runs Ubuntu 22.04/24.04):
```bash
# GSWiki
source server/config/gswiki.conf && sudo bash server/setup-mediawiki.sh
source server/config/gswiki.conf && python3 server/import-content.py --full

# Elanthipedia
source server/config/elanthipedia.conf && sudo bash server/setup-mediawiki.sh
```

Import modes:
- `--full` - All pages across all namespaces (several hours)
- `--templates` - Templates, categories, MediaWiki pages only (namespaces 4, 6, 8, 10, 14)
- `--recent` - Recently changed pages
- `--images` - Download and import images

Static mirror:
```bash
source server/config/gswiki.conf && bash server/create-static-mirror.sh          # Full
source server/config/gswiki.conf && bash server/create-static-mirror.sh --quick  # Limited depth
```

For long-running tasks (full import, full mirror), use `screen -S gswiki` to avoid disconnect issues.

## Architecture

### Config-Driven Multi-Wiki Support
- [server/config/gswiki.conf](server/config/gswiki.conf) / [server/config/elanthipedia.conf](server/config/elanthipedia.conf) define wiki-specific settings
- Scripts use environment variables: `WIKI_ID`, `SOURCE_WIKI`, `SOURCE_API`, `WIKI_DIR`, `DB_NAME`, etc.
- Each wiki has separate MediaWiki installation, database, and domain

### Shared Library (lib/)
Common functionality used by both `scripts/` and `server/` scripts:
- `WikiAPI` - MediaWiki API client with rate limiting, retries, pagination
- `setup_logging` - Configures file + console logging with rotation
- `title_to_filename` / `filename_to_title` - Safe filename conversion

### Key Components
| Component | Purpose |
|-----------|---------|
| `lib/wiki_api.py` | Shared MediaWiki API client |
| `lib/logging_config.py` | Logging setup with file rotation |
| `server/import-content.py` | Fetches pages via MediaWiki API and imports via maintenance scripts |
| `server/setup-mediawiki.sh` | Installs Nginx, PHP, MariaDB, MediaWiki 1.41 |
| `server/fix-styling.sh` | Applies archive logo, CSS, banner, hides edit UI |
| `server/create-static-mirror.sh` | Creates offline archive via wget + post-processing |
| `server/fix-static-mirror.py` | Makes static HTML work offline (embeds CSS, fixes links) |
| `server/weekly-update.sh` | Cron script for incremental updates |
| `scripts/crawl.py` | GitHub Pages crawler with link rewriting |
| `config.json` | GitHub Pages configuration (crawl settings, user agent) |

### Content Import Behavior
- MediaWiki import (`import-content.py`) imports **all namespaces** including User/Talk pages
- Import automatically toggles `$wgReadOnly` in LocalSettings.php during operation
- After import, runs `rebuildtextindex.php` and `refreshLinks.php` maintenance scripts

### GitHub Actions
[.github/workflows/weekly-crawl.yml](.github/workflows/weekly-crawl.yml) runs weekly (Sunday 3 AM UTC) to update GitHub Pages archive via crawl + Pagefind search indexing.

## File Naming Convention

Static pages (GitHub Pages) use escaped filenames for special characters:
- `/` → `_SLASH_`, `:` → `_COLON_`, `?` → `_QUESTION_`, `*` → `_STAR_`, etc.

See `title_to_filename()` in [scripts/crawl.py](scripts/crawl.py).
