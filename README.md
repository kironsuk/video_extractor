# dvdrip

Command-line tool for extracting video from physical DVDs. Works on macOS and Windows.

## Requirements

- Python 3.10+
- [HandBrakeCLI](https://handbrake.fr/downloads2.php)
- [libdvdcss](https://www.videolan.org/developers/libdvdcss.html) (for encrypted/commercial DVDs)

## Installation

### macOS

```bash
# Install dependencies
brew install handbrake libdvdcss

# Install dvdrip
pip install -e .
```

### Windows

**HandBrakeCLI** — install one of:
- Download from https://handbrake.fr/downloads2.php and add to PATH
- `choco install handbrake-cli`

**libdvdcss** — download `libdvdcss-2.dll` from https://www.videolan.org/developers/libdvdcss.html and place it next to `HandBrakeCLI.exe`.

```powershell
# Install dvdrip
pip install -e .
```

### Windows standalone .exe

If you don't want to install Python on the target machine:

```powershell
pip install -e ".[build]"
python scripts/build_exe.py
# Produces dist/dvdrip.exe
```

## Usage

```bash
# Verify dependencies are installed
dvdrip check

# Scan the inserted DVD to see available titles
dvdrip scan

# Rip the main feature
dvdrip rip --main-feature

# Rip a specific title
dvdrip rip --title 2

# Rip all titles longer than 1 minute
dvdrip rip --all-titles

# Customize output
dvdrip rip --title 1 --format mp4 --codec h264 --quality 18 --output ~/Movies

# Filter audio/subtitle tracks by language
dvdrip rip --main-feature --audio-lang eng --subtitle-lang eng
```

### Options

| Flag | Description |
|---|---|
| `--drive, -d` | Device path (auto-detected if omitted) |
| `--output, -o` | Output directory (default: current dir) |
| `--format, -f` | Container: `mkv` (default) or `mp4` |
| `--codec, -c` | Video codec: `h265` (default) or `h264` |
| `--quality, -q` | RF quality value 0-51 (default: 20, lower = better) |
| `--title, -t` | Rip a specific title number |
| `--main-feature` | Auto-select the main feature |
| `--all-titles` | Rip all titles longer than 1 minute |
| `--audio-lang` | Preferred audio language code (e.g. `eng`) |
| `--subtitle-lang` | Subtitle language to include (e.g. `eng`) |

## Using HandBrakeCLI directly

If you prefer to use HandBrakeCLI without dvdrip, here are the raw commands.

### Scan the disc to see all titles

**macOS:**
```bash
HandBrakeCLI -i /dev/disk4 -t 0 --scan
```
Replace `/dev/disk4` with your optical drive — run `diskutil list` to find it.

**Windows:**
```powershell
HandBrakeCLI -i D: -t 0 --scan
```

### Rip a specific title

**macOS:**
```bash
HandBrakeCLI -i /dev/disk4 -t 1 -o ~/Movies/movie.mkv \
  --format av_mkv \
  --encoder x265 \
  --quality 20 \
  --audio 1 \
  --aencoder copy
```

**Windows:**
```powershell
HandBrakeCLI -i D: -t 1 -o C:\Videos\movie.mkv `
  --format av_mkv `
  --encoder x265 `
  --quality 20 `
  --audio 1 `
  --aencoder copy
```

### Rip all audio and subtitle tracks

```bash
HandBrakeCLI -i /dev/disk4 -t 1 -o movie.mkv \
  --format av_mkv \
  --encoder x265 \
  --quality 20 \
  --all-audio \
  --all-subtitles
```

### Key flags

| Flag | What it does |
|---|---|
| `-i` | Input source (drive device path) |
| `-t` | Title number (`0` = scan all, `1`+ = rip that title) |
| `-o` | Output file path |
| `--format` | `av_mkv` or `av_mp4` |
| `--encoder` | `x265` (smaller files) or `x264` (more compatible) |
| `--quality` | RF value: 18-22 is typical (lower = better quality, bigger file) |
| `--audio` | Audio track numbers (comma-separated, e.g. `1,2`) |
| `--aencoder` | `copy` keeps original audio, or `av_aac` to re-encode |
| `--subtitle` | Subtitle track numbers (e.g. `1`) |

### Notes

- **libdvdcss** is required for encrypted/commercial DVDs — without it HandBrakeCLI will fail to read the disc
- Quality 20 is a good default. Use 18 for higher quality, 22 for smaller files
- `x264` is more widely compatible; `x265` gives ~30% smaller files at the same quality

## Development

```bash
# Install with test dependencies
pip install -e ".[test]"

# Run tests
pytest -v
```
