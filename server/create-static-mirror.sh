#!/bin/bash
#
# Wiki Archive - Static Mirror Creator
# Creates a downloadable static HTML snapshot of a wiki
#
# Usage:
#   source server/config/gswiki.conf && bash server/create-static-mirror.sh
#   source server/config/gswiki.conf && bash server/create-static-mirror.sh --quick
#
# Output: /var/www/{wiki}-archive/downloads/{wiki}-static-YYYY-MM-DD.tar.gz
#

set -e

# Check if config was sourced
if [ -z "$WIKI_ID" ]; then
    echo "ERROR: No wiki configuration loaded!"
    echo ""
    echo "Usage:"
    echo "  source server/config/gswiki.conf && bash server/create-static-mirror.sh"
    echo "  source server/config/elanthipedia.conf && bash server/create-static-mirror.sh"
    exit 1
fi

# Configuration (from sourced config file)
# SOURCE_WIKI, WIKI_DIR, STATIC_PREFIX, KEEP_ARCHIVES come from config
WORK_DIR="/tmp/${WIKI_ID}-mirror"
OUTPUT_DIR="${DOWNLOADS_DIR:-${WIKI_DIR}/downloads}"
DATE=$(date '+%Y-%m-%d')
ARCHIVE_NAME="${STATIC_PREFIX}-${DATE}"
DELAY=1          # Seconds between requests (be polite)

# Parse arguments
QUICK_MODE=false
if [ "$1" = "--quick" ]; then
    QUICK_MODE=true
    echo "Quick mode: limiting crawl depth"
fi

echo "=========================================="
echo "  ${WIKI_NAME} Static Mirror Creator"
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

echo "[1/5] Crawling wiki with wget..."

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
    --user-agent="${WIKI_NAME}-Archiver/1.0 (archival purposes)"
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
echo "[2/5] Cleaning up unnecessary files..."

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
echo "[3/5] Fixing HTML for offline viewing..."

# Run the Python fix script to embed CSS and fix links
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/fix-static-mirror.py" "$WORK_DIR/$ARCHIVE_NAME" --wiki-name "${WIKI_NAME}" --live-url "${SOURCE_WIKI}" 2>&1 | tail -5

echo ""
echo "[4/5] Creating archive..."

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
echo "[5/5] Cleaning up old archives..."

# Keep only the last N archives
cd "$OUTPUT_DIR"
ls -t ${STATIC_PREFIX}-*.tar.gz 2>/dev/null | tail -n +$((KEEP_ARCHIVES + 1)) | xargs -r rm -f

# List current archives
echo "  Current archives:"
ls -lh ${STATIC_PREFIX}-*.tar.gz 2>/dev/null | awk '{print "    " $9 " (" $5 ")"}'

# Keep work directory for debugging/re-processing (cleaned on next run)
# To manually re-process after fixing scripts:
#   python3 server/fix-static-mirror.py /tmp/${WIKI_ID}-mirror/${STATIC_PREFIX}-YYYY-MM-DD --wiki-name "..." --live-url "..."
#   cd /tmp/${WIKI_ID}-mirror && tar -czf ${WIKI_DIR}/downloads/${STATIC_PREFIX}-YYYY-MM-DD.tar.gz ${STATIC_PREFIX}-YYYY-MM-DD
echo "  Work files kept at: $WORK_DIR/$ARCHIVE_NAME"

echo ""
echo "=========================================="
echo "  Done!"
echo "=========================================="
echo ""
echo "Download URL: https://${ARCHIVE_DOMAIN}/downloads/$ARCHIVE_NAME.tar.gz"
echo "Latest URL:   https://${ARCHIVE_DOMAIN}/downloads/latest.tar.gz"
echo ""
echo "To extract: tar -xzf $ARCHIVE_NAME.tar.gz"
echo "Then open:  $ARCHIVE_NAME/${STATIC_MAIN_PAGE}.html"
echo ""
