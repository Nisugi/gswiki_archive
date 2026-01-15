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
curl -s -o "$WIKI_DIR/resources/assets/wiki-logo.png" "https://gswiki.play.net/resources/assets/wiki.png"

# Import styling pages from live wiki
echo "Importing CSS and sidebar from live wiki..."
for PAGE in "MediaWiki:Common.css" "MediaWiki:Vector.css" "MediaWiki:Common.js" "MediaWiki:Sidebar"; do
  echo "  Importing $PAGE..."
  curl -s "https://gswiki.play.net/api.php?action=query&titles=$PAGE&export=1&exportnowrap=1&format=xml" > /tmp/page.xml
  php "$WIKI_DIR/maintenance/importDump.php" /tmp/page.xml 2>/dev/null
done

# Add archive customizations to LocalSettings.php
echo "Adding archive customizations..."

# Check if our customizations already exist
if ! grep -q "ARCHIVE STYLING" "$WIKI_DIR/LocalSettings.php"; then
  cat >> "$WIKI_DIR/LocalSettings.php" << 'SETTINGS'

## ================================================
## ARCHIVE STYLING - Match live wiki appearance
## ================================================

# Use the same logo as live wiki
$wgLogos = [
    '1x' => "$wgResourceBasePath/resources/assets/wiki-logo.png",
];

# Hide login/account elements and add archive banner via CSS
$wgHooks['BeforePageDisplay'][] = function ( OutputPage &$out, Skin &$skin ) {
    $out->addInlineStyle('
        /* Hide login and account creation */
        #pt-login, #pt-login-2, #pt-createaccount, #pt-anonuserpage,
        .mw-portlet-personal, #p-personal,
        #ca-viewsource, #ca-edit, #ca-history,
        .vector-user-links { display: none !important; }

        /* Hide sitenotice (we use fixed banner instead) */
        #siteNotice { display: none !important; }

        /* Fixed archive banner at top */
        body::before {
            content: "ARCHIVED SNAPSHOT of GSWiki • View live wiki at gswiki.play.net";
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
        }

        /* Push page content down to account for fixed banner */
        body { padding-top: 45px !important; }
    ');
    return true;
};
SETTINGS
fi

# Clear caches
echo "Clearing caches..."
php "$WIKI_DIR/maintenance/rebuildLocalisationCache.php" --force 2>/dev/null || true

# Re-enable read-only
echo "Re-enabling read-only mode..."
sed -i 's/^# \$wgReadOnly/$wgReadOnly/' "$WIKI_DIR/LocalSettings.php"

echo ""
echo "=== Done! ==="
echo "Refresh the page to see the updated styling."
