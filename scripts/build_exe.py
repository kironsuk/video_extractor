#!/usr/bin/env python3
"""Build dvdrip.exe using PyInstaller.

Run this on Windows:
    python scripts/build_exe.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "dvdrip.spec"
DIST = ROOT / "dist"


def main() -> None:
    print("Installing build dependencies...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-e", ".[build]"],
        cwd=ROOT,
    )

    print(f"\nBuilding with spec: {SPEC}")
    subprocess.check_call(
        [sys.executable, "-m", "PyInstaller", str(SPEC), "--clean"],
        cwd=ROOT,
    )

    exe = DIST / "dvdrip.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        print(f"\nBuild complete: {exe}")
        print(f"Size: {size_mb:.1f} MB")
    else:
        # On non-Windows the output won't have .exe extension
        candidates = list(DIST.glob("dvdrip*"))
        if candidates:
            out = candidates[0]
            size_mb = out.stat().st_size / (1024 * 1024)
            print(f"\nBuild complete: {out}")
            print(f"Size: {size_mb:.1f} MB")
        else:
            print("\nBuild finished but output not found in dist/", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
