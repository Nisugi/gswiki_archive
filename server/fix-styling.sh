#!/bin/bash
#
# GSWiki Archive - Fix Styling Script
# Makes the archive look exactly like the live wiki
# Run as root on the VPS
#

set -e

WIKI_DIR="/var/www/gswiki-archive"

echo "=== Fixing GSWiki Archive Styling ==="

# Disable read-only
echo "Disabling read-only mode..."
sed -i 's/^\$wgReadOnly/# $wgReadOnly/' "$WIKI_DIR/LocalSettings.php"

# Download the logo
echo "Downloading wiki logo..."
mkdir -p "$WIKI_DIR/resources/assets"
curl -s -o "$WIKI_DIR/resources/assets/wiki.png" "https://gswiki.play.net/resources/assets/wiki.png"
chown www-data:www-data "$WIKI_DIR/resources/assets/wiki.png"

# Import styling pages from live wiki
echo "Importing CSS and sidebar from live wiki..."
for PAGE in "MediaWiki:Common.css" "MediaWiki:Vector.css" "MediaWiki:Common.js" "MediaWiki:Sidebar"; do
  echo "  Importing $PAGE..."
  curl -s "https://gswiki.play.net/api.php?action=query&titles=$PAGE&export=1&exportnowrap=1&format=xml" > /tmp/page.xml
  php "$WIKI_DIR/maintenance/importDump.php" /tmp/page.xml 2>/dev/null
done

# Remove old ARCHIVE STYLING block if it exists (we'll add updated version)
echo "Updating LocalSettings.php..."
sed -i '/## ARCHIVE STYLING/,/^};$/d' "$WIKI_DIR/LocalSettings.php"

# Add archive customizations to LocalSettings.php
cat >> "$WIKI_DIR/LocalSettings.php" << 'SETTINGS'

## ================================================
## ARCHIVE STYLING - Match live wiki appearance
## ================================================

# Use legacy Vector skin (with permanent sidebar, not collapsible)
$wgDefaultSkin = 'vector';
$wgVectorDefaultSkinVersion = '1';

# Use the same logo as live wiki
$wgLogo = "$wgResourceBasePath/resources/assets/wiki.png";

# Hide login/account elements and add archive banner via CSS
$wgHooks['BeforePageDisplay'][] = function ( OutputPage &$out, Skin &$skin ) {
    $out->addInlineStyle('
        /* Hide login and account creation */
        #pt-login, #pt-login-2, #pt-createaccount, #pt-anonuserpage,
        #pt-preferences, #pt-watchlist, #pt-mycontris, #pt-mytalk,
        #p-personal, .vector-user-links,
        #ca-viewsource, #ca-edit, #ca-history, #ca-watch, #ca-unwatch,
        .mw-editsection { display: none !important; }

        /* Hide sitenotice (we use fixed banner instead) */
        #siteNotice { display: none !important; }

        /* Fixed archive banner at top */
        body::before {
            content: "ARCHIVED SNAPSHOT of GSWiki • Visit gswiki.play.net for live wiki";
            display: block;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-bottom: 3px solid #e94560;
            color: white;
            text-align: center;
            padding: 8px 20px;
            font-weight: bold;
            z-index: 9999;
            font-size: 14px;
        }

        /* Push page content down to account for fixed banner */
        body { margin-top: 40px !important; }
    ');
    return true;
};
SETTINGS

# Clear caches
echo "Clearing caches..."
php "$WIKI_DIR/maintenance/rebuildLocalisationCache.php" --force 2>/dev/null || true
rm -rf "$WIKI_DIR/cache/*" 2>/dev/null || true

# Re-enable read-only
echo "Re-enabling read-only mode..."
sed -i 's/^# \$wgReadOnly/$wgReadOnly/' "$WIKI_DIR/LocalSettings.php"

echo ""
echo "=== Done! ==="
echo "Refresh the page (Ctrl+Shift+R to bypass cache) to see changes."
echo ""
echo "NOTE: Images still need to be imported separately:"
echo "  python3 /root/gswiki_archive/server/import-content.py --images"
