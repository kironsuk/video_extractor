"""Dependency detection for external tools."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DepStatus:
    name: str
    found: bool
    path: str | None = None
    install_hint: str = ""


def check_handbrake() -> DepStatus:
    """Check if HandBrakeCLI is available."""
    path = shutil.which("HandBrakeCLI")
    if path:
        return DepStatus("HandBrakeCLI", found=True, path=path)

    # Check common Homebrew paths
    for candidate in (
        "/opt/homebrew/bin/HandBrakeCLI",
        "/usr/local/bin/HandBrakeCLI",
    ):
        if Path(candidate).is_file():
            return DepStatus("HandBrakeCLI", found=True, path=candidate)

    return DepStatus(
        "HandBrakeCLI",
        found=False,
        install_hint="brew install handbrake",
    )


def check_libdvdcss() -> DepStatus:
    """Check if libdvdcss is installed."""
    # Check common library paths
    for lib_dir in ("/opt/homebrew/lib", "/usr/local/lib"):
        lib_path = Path(lib_dir)
        if lib_path.exists():
            matches = list(lib_path.glob("libdvdcss*"))
            if matches:
                return DepStatus(
                    "libdvdcss", found=True, path=str(matches[0])
                )

    # Fallback: ask brew
    try:
        result = subprocess.run(
            ["brew", "list", "libdvdcss"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return DepStatus("libdvdcss", found=True, path="(brew)")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return DepStatus(
        "libdvdcss",
        found=False,
        install_hint="brew install libdvdcss",
    )


def check_all() -> list[DepStatus]:
    """Check all dependencies and return their statuses."""
    return [check_handbrake(), check_libdvdcss()]


def get_handbrake_path() -> str:
    """Return the path to HandBrakeCLI, or raise if not found."""
    status = check_handbrake()
    if not status.found or not status.path:
        raise FileNotFoundError(
            "HandBrakeCLI not found. Install with: brew install handbrake"
        )
    return status.path
