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

# Check if our archive styling block already exists
if grep -q "## ARCHIVE STYLING - Match live wiki" "$WIKI_DIR/LocalSettings.php"; then
  echo "Archive styling block already exists, skipping..."
else
  echo "Adding archive styling block..."
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

# Enable Semantic MediaWiki (for {{#ask:}} queries in announcements, etc.)
wfLoadExtension( 'SemanticMediaWiki' );
enableSemantics( 'gswiki-archive.gs-game.uk' );

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

        /* Fixed archive banner at top - must be above everything */
        body { margin-top: 40px !important; }
        #mw-page-base { top: 40px !important; }
        #mw-head-base { top: 40px !important; }
        #mw-head { top: 40px !important; }
        #mw-panel { top: 200px !important; }
        #p-logo { top: 45px !important; }

        /* Break stacking context on navigation wrapper */
        #mw-navigation { z-index: auto !important; }

        /* Force all fixed/absolute elements below banner */
        #mw-head, #mw-panel, #p-logo, .mw-logo,
        #mw-page-base, #mw-head-base { z-index: 1 !important; }

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
            z-index: 2147483647 !important;
            font-size: 14px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }
        #archive-banner .archive-label { color: #e94560; }
        #archive-banner a { color: #7dd3fc; text-decoration: none; }
        #archive-banner a:hover { text-decoration: underline; }
    ');

    $out->prependHTML('<div id="archive-banner"><span class="archive-label">ARCHIVED SNAPSHOT</span> of GSWiki (' . htmlspecialchars($archiveDate) . ') • <a href="https://gswiki.play.net">View live wiki →</a></div>');
    return true;
};
SETTINGS
fi

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
