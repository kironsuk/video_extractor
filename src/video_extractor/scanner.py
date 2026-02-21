"""DVD metadata scanning via HandBrakeCLI."""

from __future__ import annotations

import json
import subprocess

from video_extractor.deps import get_handbrake_path
from video_extractor.models import (
    AudioTrack,
    Chapter,
    DiscInfo,
    DVDInfo,
    SubtitleTrack,
    Title,
)


class ScanError(Exception):
    """Raised when DVD scanning fails."""


def scan_disc(disc: DiscInfo) -> DVDInfo:
    """Scan a DVD disc and return structured metadata.

    Uses HandBrakeCLI's JSON scan mode to enumerate all titles,
    their chapters, audio tracks, and subtitle tracks.
    """
    handbrake = get_handbrake_path()

    try:
        result = subprocess.run(
            [
                handbrake,
                "-i", disc.device_path,
                "-t", "0",
                "--scan",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        raise ScanError("Disc scan timed out. The disc may be damaged or unsupported.")
    except subprocess.SubprocessError as e:
        raise ScanError(f"Failed to scan disc: {e}")

    # HandBrakeCLI outputs JSON after a "JSON Title Set:" prefix line,
    # mixed with other stderr output. The JSON is on stderr.
    raw = result.stderr
    json_data = _extract_json(raw)
    if json_data is None:
        raise ScanError(
            "Failed to read disc. It may be damaged or unsupported."
        )

    titles = _parse_titles(json_data)
    return DVDInfo(disc=disc, titles=titles)


def _extract_json(output: str) -> dict | None:
    """Extract the JSON payload from HandBrakeCLI scan output."""
    marker = "JSON Title Set:"
    idx = output.find(marker)
    if idx == -1:
        return None

    json_str = output[idx + len(marker):]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def _parse_titles(data: dict) -> list[Title]:
    """Parse HandBrakeCLI JSON scan data into Title objects."""
    titles = []
    for t in data.get("TitleList", []):
        duration = t.get("Duration", {})
        total_seconds = (
            duration.get("Hours", 0) * 3600
            + duration.get("Minutes", 0) * 60
            + duration.get("Seconds", 0)
        )

        chapters = [
            Chapter(
                number=i + 1,
                duration_ms=(
                    ch.get("Duration", {}).get("Hours", 0) * 3600000
                    + ch.get("Duration", {}).get("Minutes", 0) * 60000
                    + ch.get("Duration", {}).get("Seconds", 0) * 1000
                ),
            )
            for i, ch in enumerate(t.get("ChapterList", []))
        ]

        audio_tracks = [
            AudioTrack(
                index=i + 1,
                codec=a.get("CodecName", a.get("Codec", "unknown")),
                language=a.get("LanguageCode", a.get("Language", "und")),
                channels=_channel_count(a.get("ChannelLayout", 0)),
                description=a.get("Description", ""),
            )
            for i, a in enumerate(t.get("AudioList", []))
        ]

        subtitle_tracks = [
            SubtitleTrack(
                index=i + 1,
                language=s.get("LanguageCode", s.get("Language", "und")),
                format=s.get("SourceName", s.get("Source", "unknown")),
                description=s.get("Description", ""),
            )
            for i, s in enumerate(t.get("SubtitleList", []))
        ]

        geometry = t.get("Geometry", {})
        width = geometry.get("Width", 0)
        height = geometry.get("Height", 0)
        resolution = f"{width}x{height}" if width and height else ""

        titles.append(
            Title(
                number=t.get("Index", 0),
                duration_seconds=total_seconds,
                chapters=chapters,
                audio_tracks=audio_tracks,
                subtitle_tracks=subtitle_tracks,
                is_main_feature=t.get("MainFeature", False),
                resolution=resolution,
            )
        )

    return titles


def _channel_count(layout: int) -> int:
    """Convert HandBrake channel layout bitmask to channel count."""
    if isinstance(layout, int) and layout > 0:
        return bin(layout).count("1")
    return 2  # default stereo
