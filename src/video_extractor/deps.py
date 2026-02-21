"""Dependency detection for external tools."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
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

    # Check platform-specific paths
    if sys.platform == "darwin":
        for candidate in (
            "/opt/homebrew/bin/HandBrakeCLI",
            "/usr/local/bin/HandBrakeCLI",
        ):
            if Path(candidate).is_file():
                return DepStatus("HandBrakeCLI", found=True, path=candidate)
        hint = "brew install handbrake"
    elif sys.platform == "win32":
        candidate = r"C:\Program Files\HandBrake\HandBrakeCLI.exe"
        if Path(candidate).is_file():
            return DepStatus("HandBrakeCLI", found=True, path=candidate)
        hint = (
            "Download from https://handbrake.fr"
            " or: choco install handbrake-cli"
        )
    else:
        hint = "Install HandBrakeCLI for your platform"

    return DepStatus("HandBrakeCLI", found=False, install_hint=hint)


def check_libdvdcss() -> DepStatus:
    """Check if libdvdcss is installed."""
    if sys.platform == "darwin":
        return _check_libdvdcss_macos()
    elif sys.platform == "win32":
        return _check_libdvdcss_windows()
    return DepStatus(
        "libdvdcss",
        found=False,
        install_hint="Install libdvdcss for your platform",
    )


def _check_libdvdcss_macos() -> DepStatus:
    """Check for libdvdcss on macOS."""
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


def _check_libdvdcss_windows() -> DepStatus:
    """Check for libdvdcss on Windows."""
    dll_name = "libdvdcss-2.dll"

    # Check alongside HandBrakeCLI executable
    hb_path = shutil.which("HandBrakeCLI")
    if hb_path:
        candidate = Path(hb_path).parent / dll_name
        if candidate.is_file():
            return DepStatus("libdvdcss", found=True, path=str(candidate))

    # Check the default HandBrake install dir
    program_files_candidate = Path(
        r"C:\Program Files\HandBrake"
    ) / dll_name
    if program_files_candidate.is_file():
        return DepStatus(
            "libdvdcss", found=True, path=str(program_files_candidate)
        )

    # Scan PATH directories for the DLL
    for dir_str in os.environ.get("PATH", "").split(";"):
        if dir_str:
            candidate = Path(dir_str) / dll_name
            if candidate.is_file():
                return DepStatus("libdvdcss", found=True, path=str(candidate))

    return DepStatus(
        "libdvdcss",
        found=False,
        install_hint=(
            "Download from"
            " https://www.videolan.org/developers/libdvdcss.html"
        ),
    )


def check_all() -> list[DepStatus]:
    """Check all dependencies and return their statuses."""
    return [check_handbrake(), check_libdvdcss()]


def get_handbrake_path() -> str:
    """Return the path to HandBrakeCLI, or raise if not found."""
    status = check_handbrake()
    if not status.found or not status.path:
        raise FileNotFoundError(
            f"HandBrakeCLI not found. Install with: {status.install_hint}"
        )
    return status.path
