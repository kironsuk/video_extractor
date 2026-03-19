#!/usr/bin/env python3
"""
split_video.py — Split an already-ripped video into clips using scene detection.

Uses PySceneDetect's AdaptiveDetector to find scene boundaries, then
splits with ffmpeg. Verifies total frame count matches the original.

Usage: python3 split_video.py <input.mp4> [output_dir]
"""

import re
import subprocess
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


def detect_scenes(input_path: str, threshold: float = 55.0, min_scene_sec: float = 60.0):
    """Detect scene boundaries using PySceneDetect's ContentDetector."""
    from scenedetect import open_video, SceneManager
    from scenedetect.detectors import ContentDetector

    video = open_video(input_path)
    fps = video.frame_rate

    sm = SceneManager()
    sm.add_detector(ContentDetector(
        threshold=threshold,
        min_scene_len=int(min_scene_sec * fps),
    ))

    print(f"Analyzing video for scene changes...")
    sm.detect_scenes(video, show_progress=True)
    scene_list = sm.get_scene_list()
    return scene_list


def split_with_ffmpeg(input_path: str, scene_list, output_dir: Path):
    """Split video into clips using ffmpeg re-encode for frame accuracy."""
    clips = []

    # Build force_key_frames arg from scene boundaries
    cut_times = [scene[0].get_seconds() for scene in scene_list[1:]]  # skip first (0.0)

    if not cut_times:
        print("Only one scene detected — nothing to split.")
        return clips

    for i, (start, end) in enumerate(scene_list):
        clip_num = i + 1
        clip_path = output_dir / f"clip_{clip_num:03d}.mp4"
        start_sec = start.get_seconds()
        end_sec = end.get_seconds()
        duration = end_sec - start_sec

        print(f"  Clip {clip_num}/{len(scene_list)}: "
              f"{start.get_timecode()} -> {end.get_timecode()} ({duration:.1f}s)")

        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
            "-ss", f"{start_sec:.3f}",
            "-to", f"{end_sec:.3f}",
            "-i", input_path,
            "-map", "0:v:0", "-map", "0:a:0", "-map_chapters", "-1",
            "-c:v", "libx264", "-crf", "18", "-preset", "slow",
            "-c:a", "aac", "-b:a", "192k",
            str(clip_path),
        ]
        subprocess.run(cmd, check=True)
        clips.append(clip_path)

    return clips


def parse_date(s: str) -> tuple[int, int, int] | None:
    """Parse 'AUG. 10 1996' into (1996, 8, 10). Returns None if year is implausible."""
    parts = s.replace(".", "").split()
    month = MONTH_ORDER.get(parts[0].upper())
    if not month:
        return None
    day = int(parts[1])
    year = int(parts[2])
    if not (1980 <= year <= 2015):
        return None
    return (year, month, day)


def filter_dates_to_range(dates: list[tuple[int, int, int]],
                          known_range: tuple[tuple[int, int, int], tuple[int, int, int]] | None
                          ) -> list[tuple[int, int, int]]:
    """Filter OCR'd dates to the known disc date range. Discard outliers."""
    if not known_range or not dates:
        return dates
    lo, hi = known_range
    return [d for d in dates if lo <= d <= hi]


def ocr_dates_from_clip(clip_path: str) -> list[tuple[int, int, int]]:
    """OCR the bottom strip of sampled frames for camcorder date stamps."""
    try:
        import cv2
        import pytesseract
    except ImportError:
        return []

    cap = cv2.VideoCapture(clip_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    dates = set()
    # Sample every 10 seconds (clips are short)
    for sec in range(0, max(int(duration), 1), 10):
        cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
        ret, frame = cap.read()
        if not ret:
            continue

        h, w = frame.shape[:2]
        crop = frame[int(h * 0.85):, :]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (gray.shape[1] * 3, gray.shape[0] * 3),
                          interpolation=cv2.INTER_CUBIC)
        _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        text = pytesseract.image_to_string(thresh, config="--psm 6")

        for match in DATE_PATTERN.finditer(text.upper()):
            parsed = parse_date(match.group())
            if parsed:
                dates.add(parsed)

    cap.release()
    return sorted(dates)


def format_date_range(dates: list[tuple[int, int, int]]) -> str:
    """Format date range as 'Jun1994-Oct1996' or 'Aug1996' if single month."""
    if not dates:
        return ""
    earliest = dates[0]
    latest = dates[-1]
    start = f"{MONTH_ABBR[earliest[1]]}{earliest[0]}"
    end = f"{MONTH_ABBR[latest[1]]}{latest[0]}"
    if start == end:
        return start
    return f"{start}-{end}"


def tag_clip(clip_path: Path, clip_num: int, date_range: str, parent_title: str):
    """Tag a clip MP4 with date metadata."""
    try:
        from mutagen.mp4 import MP4
    except ImportError:
        return

    mp4 = MP4(str(clip_path))
    name = f"{parent_title} - Clip {clip_num}"
    if date_range:
        name = f"{parent_title} - Clip {clip_num} ({date_range})"
        mp4["\xa9day"] = [date_range]
        mp4["desc"] = [f"Clip {clip_num} from {parent_title}. Dates: {date_range}."]
    mp4["\xa9nam"] = [name]
    mp4["\xa9too"] = ["HandBrakeCLI + dvdrip"]
    mp4.save()


def count_frames(path: str) -> int:
    """Get exact frame count by decoding every frame."""
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-count_frames",
        "-show_entries", "stream=nb_read_frames",
        "-of", "csv=p=0",
        path,
    ], capture_output=True, text=True, check=True)
    return int(result.stdout.strip())


def verify(original: str, clips: list[Path]):
    """Verify total clip frames match the original."""
    print("\nVerifying frame counts (this takes a while)...")
    orig_count = count_frames(original)
    print(f"  Original: {orig_count} frames")

    total = 0
    for clip in clips:
        c = count_frames(str(clip))
        total += c

    print(f"  Clips total: {total} frames")
    diff = orig_count - total
    print(f"  Difference: {diff} frames")

    if abs(diff) <= len(clips):
        # Allow up to 1 frame per cut point (rounding at boundaries)
        print("  PASS (within tolerance)")
    else:
        print("  WARNING: significant frame count difference")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input.mp4> [output_dir]")
        sys.exit(1)

    input_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = Path(sys.argv[2])
    else:
        output_dir = Path(input_path).parent / "clips"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Detect scenes
    scenes = detect_scenes(input_path)
    print(f"\nFound {len(scenes)} scenes:")
    for i, (start, end) in enumerate(scenes):
        dur = end.get_seconds() - start.get_seconds()
        print(f"  {i+1}. {start.get_timecode()} -> {end.get_timecode()} ({dur:.1f}s)")

    if len(scenes) <= 1:
        print("\nOnly one scene — nothing to split.")
        return

    print(f"\nSplitting into {len(scenes)} clips...")
    clips = split_with_ffmpeg(input_path, scenes, output_dir)

    if clips:
        verify(input_path, clips)

        # First, OCR the full video to establish the known date range
        print(f"\nDetecting disc date range from full video...")
        from tag_video import extract_dates_from_video
        all_dates = extract_dates_from_video(input_path)
        known_range = (all_dates[0], all_dates[-1]) if all_dates else None
        if known_range:
            disc_range = format_date_range(all_dates)
            print(f"  Disc date range: {disc_range}")
            print(f"  Clip dates outside this range will be discarded.")

        # Tag each clip with dates from its frames
        parent_title = Path(input_path).stem
        print(f"\nTagging clips with date metadata...")
        for i, clip in enumerate(clips):
            dates = ocr_dates_from_clip(str(clip))
            dates = filter_dates_to_range(dates, known_range)
            date_range = format_date_range(dates)
            tag_clip(clip, i + 1, date_range, parent_title)
            if date_range:
                print(f"  clip_{i+1:03d}: {date_range}")
            else:
                print(f"  clip_{i+1:03d}: (no date stamp found)")

        print(f"\nClips saved to: {output_dir}/")


if __name__ == "__main__":
    main()
