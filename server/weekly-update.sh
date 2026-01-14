#!/bin/bash
#
# GSWiki Archive - Weekly Update Script
# Add to crontab: 0 3 * * 0 /root/gswiki_archive/server/weekly-update.sh >> /var/log/gswiki-update.log 2>&1
#

echo ""
echo "========================================"
echo "GSWiki Archive Update - $(date)"
echo "========================================"

cd /root/gswiki_archive

# Pull latest changes from GitHub
git pull

# Run incremental import (recent changes only)
python3 server/import-content.py --recent

echo ""
echo "Update complete: $(date)"
