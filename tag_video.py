#!/usr/bin/env python3
"""
tag_video.py — Extract date range from video frames via OCR and tag MP4.

Samples frames from the ripped video, OCRs the bottom strip where camcorder
date stamps appear, then writes metadata to the MP4.

Usage: python3 tag_video.py <mp4_file> <disc_title> <order_id> [date_range]
"""

import re
import sys
from pathlib import Path

DATE_PATTERN = re.compile(
    r"(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\.?\s+\d{1,2}\s+\d{4}"
)

MONTH_ORDER = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}

MONTH_ABBR = {v: k.capitalize() for k, v in MONTH_ORDER.items()}


def parse_date(s: str) -> tuple[int, int, int] | None:
    """Parse 'AUG. 10 1996' into (1996, 8, 10). Returns None if year is implausible."""
    parts = s.replace(".", "").split()
    month = MONTH_ORDER.get(parts[0].upper())
    if not month:
        return None
    day = int(parts[1])
    year = int(parts[2])
    # Filter out OCR errors — home videos are realistically 1980–2015
    if not (1980 <= year <= 2015):
        return None
    return (year, month, day)


def extract_dates_from_video(mp4_path: str) -> list[tuple[int, int, int]]:
    """Sample video frames and OCR the bottom strip for date stamps."""
    try:
        import cv2
        import pytesseract
    except ImportError:
        print("Warning: opencv/pytesseract not installed, skipping video OCR.")
        return []

    cap = cv2.VideoCapture(mp4_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    dates = set()

    # Sample every 30 seconds
    for sec in range(0, int(duration), 30):
        cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
        ret, frame = cap.read()
        if not ret:
            continue

        h, w = frame.shape[:2]
        # Date stamps are in the bottom ~15% of the frame
        crop = frame[int(h * 0.85):, :]

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (gray.shape[1] * 3, gray.shape[0] * 3),
                          interpolation=cv2.INTER_CUBIC)

        # Binary threshold — date stamps are bright text on video
        _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        text = pytesseract.image_to_string(thresh, config="--psm 6")

        for match in DATE_PATTERN.finditer(text.upper()):
            parsed = parse_date(match.group())
            if parsed:
                dates.add(parsed)

    cap.release()
    return sorted(dates)


def format_date_range(dates: list[tuple[int, int, int]]) -> str:
    """Format as 'Jun1994-Oct1996'."""
    if not dates:
        return ""
    earliest = dates[0]
    latest = dates[-1]
    start = f"{MONTH_ABBR[earliest[1]]}{earliest[0]}"
    end = f"{MONTH_ABBR[latest[1]]}{latest[0]}"
    if start == end:
        return start
    return f"{start}-{end}"


def tag_mp4(mp4_path: Path, title: str, order_id: str, date_range: str):
    """Write metadata tags to the MP4 file."""
    from mutagen.mp4 import MP4

    mp4 = MP4(str(mp4_path))

    mp4["\xa9cmt"] = [f"YesVideo Order {order_id} via Costco"]
    mp4["\xa9too"] = ["HandBrakeCLI + dvdrip"]

    if date_range:
        mp4["\xa9nam"] = [f"{title} ({date_range})"]
        mp4["\xa9day"] = [date_range]
        mp4["desc"] = [f"Home videos from {date_range}. YesVideo Order #{order_id} (Costco)."]
    else:
        mp4["\xa9nam"] = [title]

    mp4.save()
    print(f"Tagged: {mp4_path}")
    for key in ["\xa9nam", "\xa9day", "\xa9cmt", "desc"]:
        if key in mp4:
            print(f"  {key}: {mp4[key][0]}")


def main():
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <mp4_file> <disc_title> <order_id> [date_range]")
        sys.exit(1)

    mp4_path = Path(sys.argv[1])
    disc_title = sys.argv[2]
    order_id = sys.argv[3]

    if len(sys.argv) > 4 and sys.argv[4]:
        date_range = sys.argv[4]
    else:
        print("Scanning video frames for date stamps...")
        dates = extract_dates_from_video(str(mp4_path))
        date_range = format_date_range(dates)
        if date_range:
            print(f"Detected date range: {date_range}")
        else:
            print("No dates detected automatically.")
            if sys.stdin.isatty():
                print("Enter date range manually (e.g. Jun1994-Jan1995), or press Enter to skip:")
                date_range = input("> ").strip()
            else:
                print("Non-interactive mode: skipping manual date entry.")
                date_range = ""

    tag_mp4(mp4_path, disc_title, order_id, date_range)

    # Write date range for shell script to use for renaming
    if date_range:
        range_file = mp4_path.parent / ".date_range"
        range_file.write_text(date_range)


if __name__ == "__main__":
    main()
