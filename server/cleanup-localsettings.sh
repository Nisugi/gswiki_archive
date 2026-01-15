#!/bin/bash
#
# Clean up LocalSettings.php by removing all duplicate styling blocks
# Run this once to fix the mess, then run fix-styling.sh
#
# Usage:
#   source server/config/gswiki.conf && bash server/cleanup-localsettings.sh
#   bash server/cleanup-localsettings.sh server/config/gswiki.conf
#

set -euo pipefail

CONFIG_FILE="${1:-}"

if [ -n "$CONFIG_FILE" ]; then
    # shellcheck disable=SC1090
    source "$CONFIG_FILE"
fi

if [ -z "${WIKI_DIR:-}" ]; then
    echo "ERROR: No wiki configuration loaded. Source server/config/<wiki>.conf or pass it as the first argument."
    exit 1
fi

SETTINGS="$WIKI_DIR/LocalSettings.php"
BACKUP="$WIKI_DIR/LocalSettings.php.backup"

echo "=== Cleaning up LocalSettings.php ==="

# Make a backup
cp "$SETTINGS" "$BACKUP"
echo "Backup saved to $BACKUP"

# Create a clean version by keeping only lines up to (and including) "# Site notice"
# Then we'll add back the essential extensions
echo "Removing all archive styling blocks..."

# Find the line number of "# Site notice" or similar marker
CUTOFF=$(grep -n "Site notice\|# Footer\|ARCHIVE STYLING" "$SETTINGS" | head -1 | cut -d: -f1 || true)

if [ -n "$CUTOFF" ]; then
    # Keep only lines before the cutoff
    head -n $((CUTOFF - 1)) "$SETTINGS" > "$SETTINGS.tmp"
    mv "$SETTINGS.tmp" "$SETTINGS"
    echo "Removed everything after line $CUTOFF"
else
    echo "Could not find marker line, manual cleanup needed"
    exit 1
fi

# Re-add the footer icons (they're useful)
cat >> "$SETTINGS" << 'FOOTER'

# Footer
$wgFooterIcons['poweredby']['gswiki'] = [
    "src" => "",
    "url" => "https://gswiki.play.net",
    "alt" => "Archived from GSWiki"
];
FOOTER

echo ""
echo "=== Cleanup complete ==="
echo "LocalSettings.php has been cleaned."
echo ""
echo "Now run: bash server/fix-styling.sh"
echo "to add the archive styling back (cleanly this time)"
