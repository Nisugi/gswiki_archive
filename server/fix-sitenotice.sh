#!/bin/bash
#
# Fix the site notice banner on an existing MediaWiki installation
# Run as root on the VPS after pulling from GitHub
#
# Usage:
#   source server/config/gswiki.conf && sudo bash server/fix-sitenotice.sh
#   source server/config/elanthipedia.conf && sudo bash server/fix-sitenotice.sh
#   sudo bash server/fix-sitenotice.sh server/config/gswiki.conf
#

set -euo pipefail

CONFIG_FILE="${1:-}"

if [ -n "$CONFIG_FILE" ]; then
    # shellcheck disable=SC1090
    source "$CONFIG_FILE"
fi

if [ -z "${WIKI_DIR:-}" ] || [ -z "${WIKI_NAME:-}" ] || [ -z "${SOURCE_WIKI:-}" ]; then
    echo "ERROR: No wiki configuration loaded. Source server/config/<wiki>.conf or pass it as the first argument."
    exit 1
fi

ADMIN_USER="${ARCHIVE_ADMIN_USER:-Admin}"

echo "Fixing site notice banner for ${WIKI_NAME}..."

# Remove the $wgSiteNotice line from LocalSettings.php (it escapes HTML)
sed -i '/\$wgSiteNotice/d' "$WIKI_DIR/LocalSettings.php"

# Create the MediaWiki:Sitenotice page using the maintenance script
# This allows proper wiki markup rendering
sudo -u www-data php "$WIKI_DIR/maintenance/edit.php" --user="${ADMIN_USER}" "MediaWiki:Sitenotice" <<WIKITEXT
<div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-bottom: 3px solid #e94560; padding: 10px 20px; text-align: center; color: white;">
'''<span style="color: #e94560;">ARCHIVED SNAPSHOT</span>''' of ${WIKI_NAME} - [${SOURCE_WIKI} View live wiki ->]
</div>
WIKITEXT

echo "Site notice fixed!"
echo "Refresh the page to see the updated banner."
