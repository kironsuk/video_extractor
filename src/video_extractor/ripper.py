"""Encoding orchestration via HandBrakeCLI."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from pathlib import Path

from video_extractor.deps import get_handbrake_path
from video_extractor.models import RipJob

# Matches: "Encoding: task 1 of 1, 42.31 % (125.4 fps, avg 130.2 fps, ETA 00h12m34s)"
PROGRESS_RE = re.compile(
    r"Encoding: task \d+ of \d+, (\d+\.\d+) %"
    r"(?:.*?ETA (\S+))?"
)


class RipError(Exception):
    """Raised when encoding fails."""


def build_command(job: RipJob) -> list[str]:
    """Build the HandBrakeCLI command line for a rip job."""
    handbrake = get_handbrake_path()

    cmd = [
        handbrake,
        "-i", job.source_device,
        "-t", str(job.title.number),
        "-o", str(job.output_path),
        "-f", job.output_format.handbrake_format,
        "-e", job.video_codec.handbrake_encoder,
        "-q", str(job.quality),
        "--encoder-preset", "medium",
        "--markers",
    ]

    # Audio tracks
    if job.audio_tracks:
        cmd.extend(["-a", ",".join(str(t) for t in job.audio_tracks)])
    cmd.extend(["-E", "copy"])

    # Subtitle tracks
    if job.subtitle_tracks:
        cmd.extend(["-s", ",".join(str(t) for t in job.subtitle_tracks)])

    return cmd


def rip_title(
    job: RipJob,
    on_progress: Callable[[float, str], None] | None = None,
) -> Path:
    """Execute a rip job and return the output path.

    Args:
        job: The rip job configuration.
        on_progress: Optional callback(percentage, eta_string) called
            as encoding progresses.

    Returns:
        The path to the encoded output file.

    Raises:
        RipError: If encoding fails.
    """
    cmd = build_command(job)

    # Ensure output directory exists
    job.output_path.parent.mkdir(parents=True, exist_ok=True)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Read stderr line-by-line for progress
    last_error_lines: list[str] = []
    assert process.stderr is not None
    for raw_line in process.stderr:
        line = raw_line.decode("utf-8", errors="replace")
        last_error_lines.append(line)
        if len(last_error_lines) > 50:
            last_error_lines.pop(0)

        if on_progress:
            match = PROGRESS_RE.search(line)
            if match:
                pct = float(match.group(1))
                eta = match.group(2) or ""
                on_progress(pct, eta)

    returncode = process.wait()

    if returncode != 0:
        error_tail = "".join(last_error_lines[-20:])
        raise RipError(
            f"Encoding failed (exit code {returncode}).\n"
            f"HandBrakeCLI output:\n{error_tail}\n"
            f"Try different settings or check if the disc is readable."
        )

    if not job.output_path.exists():
        raise RipError(
            "Encoding completed but output file was not created. "
            "Check disc and try again."
        )

    return job.output_path
