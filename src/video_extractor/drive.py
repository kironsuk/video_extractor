"""macOS DVD drive detection."""

from __future__ import annotations

import subprocess
from pathlib import Path

from video_extractor.models import DiscInfo


class DriveError(Exception):
    """Raised when DVD drive or disc cannot be found."""


def detect_disc() -> DiscInfo:
    """Detect a mounted DVD disc on macOS.

    Checks for optical media via diskutil, then verifies a VIDEO_TS directory
    exists at the mount point.

    Raises:
        DriveError: If no drive, no disc, or no DVD-Video is found.
    """
    device = _find_optical_device()
    mount_point, volume_label = _find_mount_point(device)
    _verify_dvd_video(mount_point)
    return DiscInfo(
        device_path=device,
        mount_point=mount_point,
        volume_label=volume_label,
    )


def _find_optical_device() -> str:
    """Find the device path of an optical disc via diskutil."""
    try:
        result = subprocess.run(
            ["diskutil", "list"],
            capture_output=True, text=True, timeout=10,
        )
    except FileNotFoundError:
        raise DriveError("diskutil not found. This tool requires macOS.")

    # Look for lines containing "optical" or "CD/DVD" type indicators.
    # diskutil list shows entries like:
    #   /dev/disk4 (external, physical):
    # We need to check each disk for optical media.
    disk_paths = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("/dev/disk") and "external" in line:
            disk_paths.append(line.split()[0])

    # Check each candidate with diskutil info for optical media
    for disk in disk_paths:
        try:
            info = subprocess.run(
                ["diskutil", "info", disk],
                capture_output=True, text=True, timeout=10,
            )
            output = info.stdout.lower()
            if any(kw in output for kw in ("dvd", "optical", "cd/dvd", "bd-rom")):
                return disk
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            continue

    # Fallback: check drutil status
    try:
        drutil = subprocess.run(
            ["drutil", "status"],
            capture_output=True, text=True, timeout=10,
        )
        output = drutil.stdout
        if "No burn support" not in output and "Type:" in output:
            # drutil reports a disc; try to find it in diskutil
            for line in output.splitlines():
                if "Name:" in line:
                    # Try to match device
                    pass
            # If drutil shows a disc but we can't find the device,
            # scan /dev/disk* for any optical mount
            for vol in Path("/Volumes").iterdir():
                if (vol / "VIDEO_TS").is_dir():
                    device = _device_for_mount(str(vol))
                    if device:
                        return device
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Last resort: check /Volumes for VIDEO_TS
    for vol in Path("/Volumes").iterdir():
        if (vol / "VIDEO_TS").is_dir():
            device = _device_for_mount(str(vol))
            if device:
                return device

    raise DriveError(
        "No DVD drive found. Connect an external DVD drive and insert a disc."
    )


def _device_for_mount(mount_point: str) -> str | None:
    """Get the /dev/disk* device for a given mount point."""
    try:
        result = subprocess.run(
            ["diskutil", "info", mount_point],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.splitlines():
            if "Device Node" in line:
                return line.split(":")[-1].strip()
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass
    return None


def _find_mount_point(device: str) -> tuple[str, str]:
    """Find the mount point and volume label for a device."""
    try:
        result = subprocess.run(
            ["diskutil", "info", device],
            capture_output=True, text=True, timeout=10,
        )
    except subprocess.SubprocessError as e:
        raise DriveError(f"Failed to query device {device}: {e}")

    mount_point = ""
    volume_label = ""

    for line in result.stdout.splitlines():
        if "Mount Point" in line:
            mount_point = line.split(":", 1)[-1].strip()
        elif "Volume Name" in line:
            volume_label = line.split(":", 1)[-1].strip()

    if not mount_point:
        raise DriveError(
            "No disc in drive. Please insert a DVD."
        )

    return mount_point, volume_label or "DVD"


def _verify_dvd_video(mount_point: str) -> None:
    """Verify the mount point contains a VIDEO_TS directory."""
    video_ts = Path(mount_point) / "VIDEO_TS"
    if not video_ts.is_dir():
        # Also check lowercase
        video_ts = Path(mount_point) / "video_ts"
        if not video_ts.is_dir():
            raise DriveError(
                "Disc is not a DVD-Video (no VIDEO_TS found)."
            )
