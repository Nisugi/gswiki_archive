#!/bin/bash
#
# Fix the site notice banner on an existing MediaWiki installation
# Run as root on the VPS after pulling from GitHub
#

set -e

WIKI_DIR="/var/www/gswiki-archive"

echo "Fixing site notice banner..."

# Remove the $wgSiteNotice line from LocalSettings.php (it escapes HTML)
sed -i '/\$wgSiteNotice/d' "$WIKI_DIR/LocalSettings.php"

# Create the MediaWiki:Sitenotice page using the maintenance script
# This allows proper wiki markup rendering
sudo -u www-data php "$WIKI_DIR/maintenance/edit.php" --user=Admin "MediaWiki:Sitenotice" <<'WIKITEXT'
<div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-bottom: 3px solid #e94560; padding: 10px 20px; text-align: center; color: white;">
'''<span style="color: #e94560;">📦 ARCHIVED SNAPSHOT</span>''' of GSWiki • [https://gswiki.play.net View live wiki →]
</div>
WIKITEXT

echo "Site notice fixed!"
echo "Refresh the page to see the updated banner."
