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

# Install Labeled Section Transclusion extension (for {{#section-h:}} used in announcements)
echo "Installing Labeled Section Transclusion extension..."
if [ ! -d "$WIKI_DIR/extensions/LabeledSectionTransclusion" ]; then
  cd "$WIKI_DIR/extensions"
  git clone https://gerrit.wikimedia.org/r/mediawiki/extensions/LabeledSectionTransclusion.git --branch REL1_41 --depth 1
  chown -R www-data:www-data LabeledSectionTransclusion
fi

# Remove ALL old ARCHIVE STYLING blocks (cleanup any duplicates)
echo "Cleaning up old styling blocks from LocalSettings.php..."
# Remove any block starting with ## ARCHIVE STYLING until };
sed -i '/## ===.*ARCHIVE STYLING/,/^};$/d' "$WIKI_DIR/LocalSettings.php"
# Also remove any standalone BeforePageDisplay hooks we added
sed -i '/\/\/ Get archive date from marker file/,/^};$/d' "$WIKI_DIR/LocalSettings.php"
# Remove any body::before CSS remnants
sed -i '/body::before/d' "$WIKI_DIR/LocalSettings.php"
# Remove empty lines at end of file
sed -i -e :a -e '/^\s*$/d;N;ba' "$WIKI_DIR/LocalSettings.php" 2>/dev/null || true

# Add archive customizations to LocalSettings.php
cat >> "$WIKI_DIR/LocalSettings.php" << 'SETTINGS'

## ================================================
## ARCHIVE STYLING - Match live wiki appearance
## ================================================

# Use legacy Vector skin (with permanent sidebar, not collapsible)
$wgDefaultSkin = 'vector';
$wgVectorDefaultSkinVersion = '1';

# Use the same logo as live wiki
$wgLogo = $wgResourceBasePath . '/resources/assets/wiki.png';

# Namespace aliases for GSWiki project pages (needed for {{Gswiki:...}} transclusions)
$wgNamespaceAliases['GSWiki'] = NS_PROJECT;
$wgNamespaceAliases['GSWiki_talk'] = NS_PROJECT_TALK;
$wgNamespaceAliases['Gswiki'] = NS_PROJECT;
$wgNamespaceAliases['Gswiki_talk'] = NS_PROJECT_TALK;

# Load Labeled Section Transclusion (for {{#section-h:}} in announcements)
wfLoadExtension( 'LabeledSectionTransclusion' );

# Hide login/account elements and add archive banner
$wgHooks['BeforePageDisplay'][] = function ( OutputPage &$out, Skin &$skin ) {
    // Get archive date from marker file
    $markerFile = '/var/www/gswiki-archive/.archive-date';
    $archiveDate = file_exists($markerFile) ? trim(file_get_contents($markerFile)) : date('M j, Y');

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
        #mw-page-base { padding-top: 40px !important; }
        #mw-head { top: 40px !important; }
        #archive-banner {
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
            z-index: 999999;
            font-size: 14px;
        }
        #archive-banner a { color: #7dd3fc; text-decoration: none; }
        #archive-banner a:hover { text-decoration: underline; }
    ');

    $out->prependHTML('<div id="archive-banner">ARCHIVED SNAPSHOT of GSWiki (' . htmlspecialchars($archiveDate) . ') • <a href="https://gswiki.play.net">View live wiki →</a></div>');
    return true;
};
SETTINGS

# Update archive date marker
echo "Updating archive date..."
date '+%b %d, %Y' > "$WIKI_DIR/.archive-date"
chown www-data:www-data "$WIKI_DIR/.archive-date"

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
