# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

macOS CLI tool (`dvdrip`) for extracting video from physical DVDs using HandBrakeCLI as the encoding engine. Python 3.10+, packaged with setuptools.

## Development Commands

```bash
# Install in editable mode
pip install -e .

# Run CLI
dvdrip check          # verify HandBrakeCLI and libdvdcss
dvdrip scan           # list titles on inserted DVD
dvdrip rip [options]  # extract video

# Run as module
python -m video_extractor
```

No test suite or linter is configured yet.

## Architecture

All source is under `src/video_extractor/`. The CLI entry point is `cli.py:cli` (Click group), registered as the `dvdrip` script.

**Data flow for `dvdrip rip`:**
`deps.py` (preflight) → `drive.py` (detect disc via diskutil/drutil) → `scanner.py` (HandBrakeCLI `--scan --json`, parse titles) → title selection (interactive via `ui.py` or flags) → `ripper.py` (build HandBrakeCLI command from `RipJob`, stream progress from stderr) → `ui.py` (Rich progress bar + completion)

**Key design points:**
- `models.py` defines all data structures; `RipJob` is the central encoding config that `ripper.py` translates into a HandBrakeCLI invocation
- `scanner.py` extracts JSON from HandBrakeCLI stderr after the `"JSON Title Set:"` marker line
- `ripper.py` parses progress via regex on stderr (`Encoding: task N of N, XX.XX %`)
- `ui.py` exports a module-level `console` singleton (Rich Console) used across all display functions
- `drive.py` supports macOS (diskutil, drutil, /Volumes/ scanning) and Windows (wmic, drive-letter detection)
- External tool imports (`deps`, `drive`, `scanner`, `ripper`, `ui`) are deferred to inside CLI command functions to keep startup fast and error messages clean
