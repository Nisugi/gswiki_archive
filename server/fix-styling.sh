#!/bin/bash
#
# GSWiki Archive - Fix Styling Script
# Makes the archive look exactly like the live wiki
# Run as root on the VPS
#

set -e

WIKI_DIR="/var/www/gswiki-archive"

echo "=== Fixing GSWiki Archive Styling ==="

# Permanently disable $wgReadOnly (it blocks thumbnail generation)
# Wiki is protected via permissions instead
echo "Disabling \$wgReadOnly (allows thumbnail generation)..."
sed -i 's/^\$wgReadOnly/# $wgReadOnly/' "$WIKI_DIR/LocalSettings.php"

# Download the logo
echo "Downloading wiki logo..."
mkdir -p "$WIKI_DIR/resources/assets"
curl -s -o "$WIKI_DIR/resources/assets/wiki.png" "https://gswiki.play.net/resources/assets/wiki.png"
chown www-data:www-data "$WIKI_DIR/resources/assets/wiki.png"

# Import styling pages from live wiki
echo "Importing CSS and sidebar from live wiki..."
for PAGE in "MediaWiki:Vector.css" "MediaWiki:Common.js" "MediaWiki:Sidebar"; do
  echo "  Importing $PAGE..."
  curl -s "https://gswiki.play.net/api.php?action=query&titles=$PAGE&export=1&exportnowrap=1&format=xml" > /tmp/page.xml
  php "$WIKI_DIR/maintenance/importDump.php" /tmp/page.xml 2>/dev/null
done

# Create custom MediaWiki:Common.css (minimal - just hide siteNotice)
echo "Creating archive CSS (MediaWiki:Common.css)..."
cat > /tmp/common-css.xml << 'CSSXML'
<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.11/">
  <page>
    <title>MediaWiki:Common.css</title>
    <ns>8</ns>
    <revision>
      <text bytes="100" xml:space="preserve">/* GSWiki Archive - Hide siteNotice (we use header notice instead) */
#siteNotice { display: none !important; }
</text>
    </revision>
  </page>
</mediawiki>
CSSXML
php "$WIKI_DIR/maintenance/importDump.php" /tmp/common-css.xml 2>/dev/null

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

# Use the same logo as live wiki (MW 1.41+ uses $wgLogos array)
$wgLogos = [ '1x' => $wgResourceBasePath . '/resources/assets/wiki.png' ];

# Enable image display (uploads still blocked by read-only mode)
$wgEnableUploads = true;
$wgUploadPath = "$wgScriptPath/images";
$wgUploadDirectory = "$IP/images";

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

# Disable account creation and login
$wgGroupPermissions['*']['createaccount'] = false;
$wgHooks['AbortLogin'][] = function() { return false; };

# Hide login UI (but keep dark mode) and add full-width archive banner
$wgHooks['BeforePageDisplay'][] = function ( OutputPage &$out, Skin &$skin ) {
    global $IP;
    $archiveDate = 'Unknown';
    $dateFile = "$IP/.archive-date";
    if ( file_exists( $dateFile ) ) {
        $archiveDate = trim( file_get_contents( $dateFile ) );
    }

    $out->addInlineStyle('
        /* Hide login UI only - keep dark mode visible */
        #pt-login, #pt-login-2, #pt-createaccount, #pt-anonuserpage,
        #pt-preferences, #pt-watchlist, #pt-mycontris, #pt-mytalk,
        #ca-viewsource, #ca-edit, #ca-history, #ca-watch, #ca-unwatch,
        .mw-editsection { display: none !important; }

        /* Full-width archive banner at top */
        #archive-banner {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 28px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-bottom: 2px solid #e94560;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            font-weight: bold;
            z-index: 1000;
        }
        #archive-banner .archive-label {
            color: #e94560;
            margin-right: 8px;
        }
        #archive-banner .archive-date {
            color: #94a3b8;
            margin-right: 8px;
        }
        #archive-banner a {
            color: #7dd3fc;
            text-decoration: none;
            margin-left: 8px;
        }
        #archive-banner a:hover { text-decoration: underline; }

        /* Push page content down for banner */
        body { margin-top: 30px !important; }
        #mw-page-base, #mw-head-base { top: 30px !important; }
        #mw-head { top: 30px !important; }
        #mw-panel { top: 190px !important; }
    ');

    // Inject full-width archive banner with date
    $out->addInlineScript('
        (function() {
            var banner = document.createElement("div");
            banner.id = "archive-banner";
            banner.innerHTML = \'<span class="archive-label">ARCHIVED SNAPSHOT</span><span class="archive-date">(' . htmlspecialchars( $archiveDate ) . ')</span> of GSWiki \u2022 <a href="https://gswiki.play.net">View live wiki \u2192</a>\';
            document.body.insertBefore(banner, document.body.firstChild);
        })();
    ');
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

echo ""
echo "=== Done! ==="
echo "Refresh the page (Ctrl+Shift+R to bypass cache) to see changes."
echo ""
echo "NOTE: Images still need to be imported separately:"
echo "  python3 /root/gswiki_archive/server/import-content.py --images"
