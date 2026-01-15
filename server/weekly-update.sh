#!/bin/bash
#
# Wiki Archive - Weekly Update Script
# Usage:
#   source server/config/gswiki.conf && bash server/weekly-update.sh
#   source server/config/elanthipedia.conf && bash server/weekly-update.sh
# Or pass a config path: bash server/weekly-update.sh server/config/gswiki.conf
#
# Suggested cron (per wiki):
#   0 3 * * 0 source /root/gswiki_archive/server/config/gswiki.conf && /root/gswiki_archive/server/weekly-update.sh >> /var/log/gswiki-update.log 2>&1
#

set -euo pipefail

CONFIG_FILE="${1:-}"

if [ -n "$CONFIG_FILE" ]; then
    # shellcheck disable=SC1090
    source "$CONFIG_FILE"
fi

if [ -z "${WIKI_ID:-}" ] || [ -z "${WIKI_NAME:-}" ] || [ -z "${WIKI_DIR:-}" ]; then
    echo "ERROR: No wiki configuration loaded. Source server/config/<wiki>.conf or pass it as the first argument."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "========================================"
echo "${WIKI_NAME} Archive Update - $(date)"
echo "========================================"

cd "$REPO_DIR"

# Pull latest changes from GitHub
git pull

# Run incremental import (recent changes only)
python3 server/import-content.py --recent

echo ""
echo "Update complete: $(date)"
