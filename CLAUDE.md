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

### VPS Server Scripts (server/)
All server scripts require sourcing a config file first:
```bash
# GSWiki
source server/config/gswiki.conf && sudo bash server/setup-mediawiki.sh
source server/config/gswiki.conf && python3 server/import-content.py --full

# Elanthipedia
source server/config/elanthipedia.conf && sudo bash server/setup-mediawiki.sh
```

Import modes:
- `--full` - All pages (several hours)
- `--templates` - Templates, categories, MediaWiki pages only (fast)
- `--recent` - Recently changed pages
- `--images` - Download and import images

## Architecture

### Config-Driven Multi-Wiki Support
- [server/config/gswiki.conf](server/config/gswiki.conf) / [server/config/elanthipedia.conf](server/config/elanthipedia.conf) define wiki-specific settings
- Scripts use environment variables from sourced config files
- Each wiki has separate MediaWiki installation, database, and domain

### Key Components
| Component | Purpose |
|-----------|---------|
| `server/import-content.py` | Fetches pages via MediaWiki API and imports via maintenance scripts |
| `server/create-static-mirror.sh` | Creates offline archive via wget + post-processing |
| `server/fix-static-mirror.py` | Makes static HTML work offline (embeds CSS, fixes links) |
| `scripts/crawl.py` | GitHub Pages crawler with link rewriting |
| `config.json` | GitHub Pages configuration (crawl settings, exclusions) |

### Content Filtering
- `User:`, `User_talk:`, `Talk:` namespaces are excluded
- Character pages using `Template:Characterprofile` are excluded unless opted in via [data/opted_in.json](data/opted_in.json)
- MediaWiki import toggles read-only mode during operation

### GitHub Actions
[.github/workflows/weekly-crawl.yml](.github/workflows/weekly-crawl.yml) runs weekly to update GitHub Pages archive via crawl + Pagefind search indexing.

## File Naming Convention

Static pages use escaped filenames for special characters:
- `/` → `_SLASH_`
- `:` → `_COLON_`
- `?` → `_QUESTION_`
- etc.

See `title_to_filename()` in [scripts/crawl.py](scripts/crawl.py).
