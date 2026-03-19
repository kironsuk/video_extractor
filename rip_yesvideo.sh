#!/usr/bin/env bash
#
# rip_yesvideo.sh — Rip a YesVideo DVD, tag with dates, and split into clips
#
# Usage: ./rip_yesvideo.sh [output_dir]
#
# Detects the mounted YesVideo disc, reads its metadata, rips the main
# title, copies metadata files, auto-detects date range via OCR, tags
# the MP4, splits into scene-based clips, and tags each clip.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_ROOT="${1:-$SCRIPT_DIR/output}"

# --- Find the YesVideo disc ---
DISC_MOUNT=""
for vol in /Volumes/*/; do
    if [[ -f "${vol}DiscMetaData.xml" && -d "${vol}VIDEO_TS" ]]; then
        DISC_MOUNT="$vol"
        break
    fi
done

if [[ -z "$DISC_MOUNT" ]]; then
    echo "Error: No YesVideo disc found. Insert a disc and try again."
    exit 1
fi

echo "Found disc at: $DISC_MOUNT"

# --- Locate helper scripts ---
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"
if [[ ! -x "$VENV_PYTHON" ]]; then
    VENV_PYTHON="python3"
fi
TAG_SCRIPT="$SCRIPT_DIR/tag_video.py"
SPLIT_SCRIPT="$SCRIPT_DIR/split_video.py"

# --- Parse metadata from DiscMetaData.xml ---
META_FILE="${DISC_MOUNT}DiscMetaData.xml"

read -r ORDER_ID TITLE_LINE <<< "$("$VENV_PYTHON" -c "
import re
with open('$META_FILE', 'rb') as f:
    text = f.read().decode('utf-16', errors='ignore')
order = re.search(r'ORDERID\s*=\s*\"([^\"]+)\"', text)
title = re.search(r'TITLELINE1\s*=\s*\"([^\"]+)\"', text)
oid = order.group(1).strip() if order else 'unknown'
tit = title.group(1).strip() if title else 'unknown'
print(oid, tit)
")"

# Clean title for use as folder name
FOLDER_NAME="$(echo "$TITLE_LINE" | sed 's/ /_/g; s/[^a-zA-Z0-9_-]//g')"
if [[ -z "$FOLDER_NAME" ]]; then
    FOLDER_NAME="YesVideo_${ORDER_ID}"
fi

DEST_DIR="$OUTPUT_ROOT/$FOLDER_NAME"

echo "Title:    $TITLE_LINE"
echo "Order ID: $ORDER_ID"
echo "Output:   $DEST_DIR"

# --- Check if already ripped ---
if [[ -d "$DEST_DIR" ]]; then
    echo ""
    echo "Warning: $DEST_DIR already exists."
    if [[ -t 0 ]]; then
        read -rp "Overwrite? [y/N] " confirm
        if [[ "$confirm" != [yY] ]]; then
            echo "Aborted."
            exit 0
        fi
    else
        echo "Non-interactive mode: skipping overwrite (use a new output dir)."
        exit 1
    fi
fi

# --- Create output directories ---
mkdir -p "$DEST_DIR/metadata"
mkdir -p "$DEST_DIR/clips"

# --- Copy metadata files ---
echo ""
echo "Copying metadata files..."
cp "$META_FILE" "$DEST_DIR/metadata/" 2>/dev/null || true

if [[ -d "${DISC_MOUNT}Photobook" ]]; then
    cp "${DISC_MOUNT}Photobook/"*.jpg "$DEST_DIR/metadata/" 2>/dev/null || true
    echo "  Copied Photobook ($(ls "${DISC_MOUNT}Photobook/"*.jpg 2>/dev/null | wc -l | tr -d ' ') pages)"
fi

if [[ -f "${DISC_MOUNT}Sheet/sheet.jpg" ]]; then
    cp "${DISC_MOUNT}Sheet/sheet.jpg" "$DEST_DIR/metadata/"
    echo "  Copied sheet.jpg"
fi

if [[ -f "${DISC_MOUNT}discsurface/discsurface.jpg" ]]; then
    cp "${DISC_MOUNT}discsurface/discsurface.jpg" "$DEST_DIR/metadata/"
    echo "  Copied discsurface.jpg"
fi

# --- Scan disc for titles ---
echo ""
echo "Scanning disc..."
SCAN_OUTPUT="$(HandBrakeCLI --scan -i "$DISC_MOUNT" 2>&1)"

MAIN_TITLE="$(echo "$SCAN_OUTPUT" | grep -E '^\+ title' | head -1 | grep -oE '[0-9]+')"
MAIN_TITLE="${MAIN_TITLE:-1}"

DURATION="$(echo "$SCAN_OUTPUT" | grep -E '^\s+\+ duration:' | head -1 | grep -oE '[0-9]{2}:[0-9]{2}:[0-9]{2}')"

echo "  Title $MAIN_TITLE: $DURATION"

# --- Rip the full video ---
OUTPUT_FILE="$DEST_DIR/${FOLDER_NAME}.mp4"
echo ""
echo "=== Ripping full video (title $MAIN_TITLE) ==="
echo ""

HandBrakeCLI \
    -i "$DISC_MOUNT" \
    -t "$MAIN_TITLE" \
    -o "$OUTPUT_FILE" \
    --preset "HQ 1080p30 Surround" \
    2>&1 | while IFS= read -r line; do
        if [[ "$line" == *"Encoding:"* ]]; then
            printf "\r%s" "$line"
        fi
    done

echo ""

if [[ ! -f "$OUTPUT_FILE" ]]; then
    echo "Error: Rip failed — output file not found."
    exit 1
fi

SIZE="$(du -h "$OUTPUT_FILE" | cut -f1 | tr -d ' ')"
echo "  Ripped: $OUTPUT_FILE ($SIZE)"

# --- Disc is no longer needed after this point ---
echo ""
echo "*** Disc is safe to eject — rip complete. ***"
echo ""
if [[ -t 0 ]]; then
    read -rp "Eject disc? [Y/n] " eject_confirm
    if [[ "$eject_confirm" != [nN] ]]; then
        drutil eject
        echo "Disc ejected. Insert the next disc when ready."
    fi
else
    echo "Non-interactive mode: skipping eject. Run 'drutil eject' manually."
fi

# --- Tag MP4 with metadata and dates ---
echo ""
echo "=== Detecting dates and tagging ==="
"$VENV_PYTHON" "$TAG_SCRIPT" "$OUTPUT_FILE" "$TITLE_LINE" "$ORDER_ID"

# Rename file with date range if detected
DATE_RANGE_FILE="$DEST_DIR/.date_range"
if [[ -f "$DATE_RANGE_FILE" ]]; then
    DATE_RANGE="$(cat "$DATE_RANGE_FILE")"
    FINAL_NAME="${FOLDER_NAME}_${DATE_RANGE}.mp4"
    FINAL_FILE="$DEST_DIR/$FINAL_NAME"
    mv "$OUTPUT_FILE" "$FINAL_FILE"
    rm "$DATE_RANGE_FILE"
    OUTPUT_FILE="$FINAL_FILE"
    echo "  Renamed to: $FINAL_NAME"
fi

# --- Split into scene-based clips ---
echo ""
echo "=== Splitting into clips ==="
"$VENV_PYTHON" "$SPLIT_SCRIPT" "$OUTPUT_FILE"

# --- Summary ---
CLIP_COUNT="$(ls "$DEST_DIR/clips/"clip_*.mp4 2>/dev/null | wc -l | tr -d ' ')"
CLIPS_SIZE="$(du -sh "$DEST_DIR/clips/" 2>/dev/null | cut -f1 | tr -d ' ')"
SIZE="$(du -h "$OUTPUT_FILE" | cut -f1 | tr -d ' ')"

echo ""
echo "==============================="
echo "Done!"
echo "  Full video: $OUTPUT_FILE ($SIZE)"
echo "  Clips: $DEST_DIR/clips/ ($CLIP_COUNT clips, $CLIPS_SIZE)"
echo "  Metadata: $DEST_DIR/metadata/"
echo "  Title: $TITLE_LINE"
echo "  Order ID: $ORDER_ID"
echo "==============================="
