# Wiki Archive

A community preservation project for game wikis, currently supporting:
- **GSWiki** (gswiki.play.net) - GemStone IV Wiki
- **Elanthipedia** (elanthipedia.play.net) - DragonRealms Wiki

**Live Archives:**
- https://gswiki-archive.gs-game.uk
- https://elanthipedia-archive.gs-game.uk (planned)

## Overview

This project provides multiple ways to preserve and access wiki content:

1. **MediaWiki Archive** - Full MediaWiki installation with imported content (primary)
2. **Static HTML Download** - Downloadable offline snapshot for local viewing
3. **GitHub Pages** - Static HTML search interface (legacy/supplementary)

## Architecture

The system uses a config-based approach to support multiple wikis:

```
┌─────────────────────────────────────────────────────┐
│                   Contabo VPS                       │
├─────────────────────────────────────────────────────┤
│  Nginx (HTTPS via Let's Encrypt)                    │
│    ├─ gswiki-archive.gs-game.uk                     │
│    └─ elanthipedia-archive.gs-game.uk              │
├─────────────────────────────────────────────────────┤
│  MediaWiki 1.41 (separate installations)            │
│    ├─ /var/www/gswiki-archive                       │
│    └─ /var/www/elanthipedia-archive                 │
├─────────────────────────────────────────────────────┤
│  MariaDB (separate databases)                       │
│    ├─ gswiki_archive                                │
│    └─ elanthipedia_archive                          │
├─────────────────────────────────────────────────────┤
│  Static Downloads                                   │
│    ├─ /var/www/gswiki-archive/downloads/            │
│    └─ /var/www/elanthipedia-archive/downloads/      │
└─────────────────────────────────────────────────────┘
```

## Directory Structure

```
gswiki_archive/
├── server/                    # VPS server scripts
│   ├── config/                # Wiki configuration files
│   │   ├── gswiki.conf        # GSWiki configuration
│   │   └── elanthipedia.conf  # Elanthipedia configuration
│   ├── setup-mediawiki.sh     # Initial MediaWiki installation
│   ├── import-content.py      # Content import from live wiki
│   ├── fix-styling.sh         # Apply archive styling/branding
│   ├── fix-sitenotice.sh      # Configure site notice
│   ├── weekly-update.sh       # Cron job for incremental updates
│   ├── create-static-mirror.sh # Create downloadable offline archive
│   ├── fix-static-mirror.py   # Post-process static files for offline viewing
│   └── nginx-downloads.conf   # Nginx config for downloads directory
├── scripts/                   # GitHub Pages scripts (legacy)
│   ├── crawl.py               # Page crawler
│   └── build_search.py        # Search index builder
├── docs/                      # GitHub Pages static site
│   ├── index.html             # Homepage with search
│   ├── wiki/                  # Archived HTML pages
│   └── assets/                # CSS/JS assets
├── data/                      # Configuration data
│   ├── opted_in.json          # Character pages that opted into archive
│   └── exclusions.json        # Pages excluded from archive
└── config.json                # Project configuration
```

## Server Setup (VPS)

### Prerequisites

- Ubuntu 22.04 or 24.04 VPS
- Root access
- Domain pointed to server IP

### 1. Initial Setup

All scripts use a config-based approach. Source the appropriate config file before running any script.

```bash
# Clone the repository
git clone https://github.com/Nisugi/gswiki_archive.git /root/gswiki_archive
cd /root/gswiki_archive

# For GSWiki:
source server/config/gswiki.conf && sudo bash server/setup-mediawiki.sh

# For Elanthipedia:
source server/config/elanthipedia.conf && sudo bash server/setup-mediawiki.sh
```

This script:
- Installs Nginx, PHP 8.x, MariaDB
- Downloads and configures MediaWiki 1.41
- Creates database and user
- Configures read-only mode
- Sets up Nginx virtual host

### 2. SSL Certificate

```bash
# Install certbot
apt install certbot python3-certbot-nginx

# Get certificate
certbot --nginx -d gswiki-archive.gs-game.uk
```

### 3. Import Content

```bash
# Install Python dependencies
pip3 install requests

# For GSWiki:
source server/config/gswiki.conf
python3 server/import-content.py --full      # Full import
python3 server/import-content.py --images    # Import images

# For Elanthipedia:
source server/config/elanthipedia.conf
python3 server/import-content.py --full
python3 server/import-content.py --images
```

Import options:
- `--full` - Import all main content pages (takes several hours)
- `--templates` - Only templates, categories, MediaWiki pages (quick)
- `--recent` - Only recently changed pages (for incremental updates)
- `--images` - Download and import all images

### 4. Apply Styling

```bash
# For GSWiki:
source server/config/gswiki.conf && sudo bash server/fix-styling.sh

# For Elanthipedia:
source server/config/elanthipedia.conf && sudo bash server/fix-styling.sh
```

This applies:
- Wiki logo from source wiki
- Custom CSS matching live wiki
- Archive banner at top of all pages
- Hide edit/login UI elements

### 5. Enable Downloads (Optional)

Add the downloads location to your Nginx config:

```bash
# Edit /etc/nginx/sites-available/gswiki-archive
# Add inside the server block (port 443):

location /downloads/ {
    alias /var/www/gswiki-archive/downloads/;
    autoindex on;
    autoindex_exact_size off;
    autoindex_localtime on;

    location ~* \.(tar\.gz|tgz|zip)$ {
        add_header Content-Disposition 'attachment';
        expires 1d;
    }
}
```

```bash
# Test and reload
nginx -t && systemctl reload nginx
```

### 6. Create Static Mirror

```bash
# For GSWiki:
source server/config/gswiki.conf && bash server/create-static-mirror.sh --quick  # Quick test
source server/config/gswiki.conf && bash server/create-static-mirror.sh           # Full mirror

# For Elanthipedia:
source server/config/elanthipedia.conf && bash server/create-static-mirror.sh
```

The static mirror:
- Uses wget to crawl the archive
- Post-processes HTML for offline viewing (embedded CSS, fixed links)
- Creates a downloadable .tar.gz file
- Available at the wiki's /downloads/ path

### 7. Weekly Updates (Cron)

```bash
# Add to root's crontab
crontab -e

# Add this line (runs every Sunday at 3 AM):
0 3 * * 0 /root/gswiki_archive/server/weekly-update.sh >> /var/log/gswiki-update.log 2>&1
```

## Server Scripts Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `setup-mediawiki.sh` | Initial MediaWiki installation | `sudo bash setup-mediawiki.sh` |
| `import-content.py` | Import pages from live wiki | `python3 import-content.py --full` |
| `fix-styling.sh` | Apply archive styling | `sudo bash fix-styling.sh` |
| `fix-sitenotice.sh` | Configure site notice | `sudo bash fix-sitenotice.sh` |
| `weekly-update.sh` | Incremental update | Runs via cron |
| `create-static-mirror.sh` | Create offline download | `bash create-static-mirror.sh` |
| `fix-static-mirror.py` | Fix static HTML for offline | Called by create-static-mirror.sh |

## Static Mirror (Offline Viewing)

The static mirror is a standalone HTML snapshot that can be viewed without any server:

1. Download from: https://gswiki-archive.gs-game.uk/downloads/latest.tar.gz
2. Extract: `tar -xzf gswiki-static-YYYY-MM-DD.tar.gz`
3. Open: `gswiki-static-YYYY-MM-DD/Main_Page.html`

Features:
- Works completely offline
- Embedded CSS (no external dependencies)
- Fixed internal links
- Archive banner indicating offline status

## Maintenance

### Running Long Tasks

For long-running operations (full import, full mirror), use screen:

```bash
# Start a screen session
screen -S gswiki

# Run your command
python3 server/import-content.py --full

# Detach: Ctrl+A, then D

# Reattach later
screen -r gswiki

# List sessions
screen -ls
```

### Viewing Logs

```bash
# Weekly update log
tail -f /var/log/gswiki-update.log

# Nginx access log
tail -f /var/log/nginx/access.log

# MediaWiki debug log (if enabled)
tail -f /var/www/gswiki-archive/cache/debug.log
```

### Clearing Caches

```bash
cd /var/www/gswiki-archive

# Clear MediaWiki cache
rm -rf cache/*
php maintenance/rebuildLocalisationCache.php --force

# Restart PHP-FPM
systemctl restart php*-fpm
```

## Character Pages

Player character pages are **excluded by default** to respect privacy. The archive imports all content from the main namespace except:
- `User:` namespace
- `User_talk:` namespace
- `Talk:` namespace

If you own a character page and want it included, please open an issue on GitHub.

## Privacy & Legal

- This is an **unofficial community project**
- Not affiliated with or endorsed by Simutronics Corporation
- GemStone IV and all related content are trademarks of Simutronics
- All wiki content belongs to its original authors and Simutronics
- For the most current information, always refer to [the live wiki](https://gswiki.play.net)

## Contributing

Contributions welcome! Please open an issue or pull request on GitHub.

## License

The archive scripts are provided as-is for community use. Wiki content remains the property of its original authors and Simutronics Corporation.
