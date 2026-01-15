#!/bin/bash
#
# GSWiki Archive - Static Mirror Creator
# Creates a downloadable static HTML snapshot of GSWiki
#
# Usage:
#   bash create-static-mirror.sh           # Full mirror
#   bash create-static-mirror.sh --quick   # Quick test (limited pages)
#
# Output: /var/www/gswiki-archive/downloads/gswiki-static-YYYY-MM-DD.tar.gz
#

set -e

# Configuration
SOURCE_WIKI="https://gswiki.play.net"
WORK_DIR="/tmp/gswiki-mirror"
OUTPUT_DIR="/var/www/gswiki-archive/downloads"
DATE=$(date '+%Y-%m-%d')
ARCHIVE_NAME="gswiki-static-${DATE}"
KEEP_ARCHIVES=5  # Keep last N archives
DELAY=1          # Seconds between requests (be polite)

# Parse arguments
QUICK_MODE=false
if [ "$1" = "--quick" ]; then
    QUICK_MODE=true
    echo "Quick mode: limiting crawl depth"
fi

echo "=========================================="
echo "  GSWiki Static Mirror Creator"
echo "=========================================="
echo ""
echo "Source: $SOURCE_WIKI"
echo "Output: $OUTPUT_DIR/$ARCHIVE_NAME.tar.gz"
echo ""

# Create directories
mkdir -p "$WORK_DIR"
mkdir -p "$OUTPUT_DIR"

# Clean previous work directory
rm -rf "$WORK_DIR/$ARCHIVE_NAME"
mkdir -p "$WORK_DIR/$ARCHIVE_NAME"

echo "[1/4] Crawling wiki with wget..."

# Build wget command
WGET_OPTS=(
    --mirror
    --convert-links
    --adjust-extension
    --page-requisites
    --no-parent
    --wait="$DELAY"
    --random-wait
    --limit-rate=500k
    --user-agent="GSWiki-Archiver/1.0 (archival purposes)"
    --reject="Special:*,action=*,oldid=*,diff=*,printable=*"
    --reject-regex="(Special:|action=|oldid=|diff=|printable=|index\.php\?)"
    --directory-prefix="$WORK_DIR/$ARCHIVE_NAME"
    --no-host-directories
    --content-disposition
    --timestamping
)

if [ "$QUICK_MODE" = true ]; then
    WGET_OPTS+=(--level=2)
else
    WGET_OPTS+=(--level=0)  # Infinite depth
fi

# Run wget (allow non-zero exit - wget returns 8 for some 404s which is fine)
wget "${WGET_OPTS[@]}" "$SOURCE_WIKI/" 2>&1 | tee "$WORK_DIR/wget.log" || true

echo ""
echo "[2/4] Cleaning up unnecessary files..."

cd "$WORK_DIR/$ARCHIVE_NAME"

# Remove query string files and duplicates
find . -name "*\?*" -delete 2>/dev/null || true
find . -name "*.orig" -delete 2>/dev/null || true

# Remove action pages, history, etc.
find . -type f \( -name "*action=*" -o -name "*oldid=*" -o -name "*diff=*" \) -delete 2>/dev/null || true

# Count files
PAGE_COUNT=$(find . -name "*.html" | wc -l)
IMAGE_COUNT=$(find . -type f \( -name "*.png" -o -name "*.gif" -o -name "*.jpg" -o -name "*.jpeg" \) | wc -l)

echo "  Pages: $PAGE_COUNT"
echo "  Images: $IMAGE_COUNT"

echo ""
echo "[3/4] Creating archive..."

cd "$WORK_DIR"

# Create tar.gz archive
tar -czf "$ARCHIVE_NAME.tar.gz" "$ARCHIVE_NAME"

# Move to output directory
mv "$ARCHIVE_NAME.tar.gz" "$OUTPUT_DIR/"

# Update 'latest' symlink
cd "$OUTPUT_DIR"
rm -f latest.tar.gz
ln -s "$ARCHIVE_NAME.tar.gz" latest.tar.gz

# Get archive size
ARCHIVE_SIZE=$(du -h "$ARCHIVE_NAME.tar.gz" | cut -f1)

echo "  Archive: $ARCHIVE_NAME.tar.gz ($ARCHIVE_SIZE)"

echo ""
echo "[4/4] Cleaning up old archives..."

# Keep only the last N archives
cd "$OUTPUT_DIR"
ls -t gswiki-static-*.tar.gz 2>/dev/null | tail -n +$((KEEP_ARCHIVES + 1)) | xargs -r rm -f

# List current archives
echo "  Current archives:"
ls -lh gswiki-static-*.tar.gz 2>/dev/null | awk '{print "    " $9 " (" $5 ")"}'

# Cleanup work directory
rm -rf "$WORK_DIR/$ARCHIVE_NAME"
rm -f "$WORK_DIR/wget.log"

echo ""
echo "=========================================="
echo "  Done!"
echo "=========================================="
echo ""
echo "Download URL: https://gswiki-archive.gs-game.uk/downloads/$ARCHIVE_NAME.tar.gz"
echo "Latest URL:   https://gswiki-archive.gs-game.uk/downloads/latest.tar.gz"
echo ""
echo "To extract: tar -xzf $ARCHIVE_NAME.tar.gz"
echo "Then open:  $ARCHIVE_NAME/index.html"
echo ""
