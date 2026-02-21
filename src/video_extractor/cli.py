"""CLI commands for DVD video extraction."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from video_extractor.models import OutputFormat, RipJob, VideoCodec


@click.group()
def cli() -> None:
    """DVD Video Extractor - rip DVDs from the command line."""


@cli.command()
def check() -> None:
    """Check that required dependencies are installed."""
    from video_extractor.deps import check_all
    from video_extractor.ui import show_dep_status

    deps = check_all()
    show_dep_status(deps)

    missing = [d for d in deps if not d.found]
    if missing:
        raise SystemExit(1)


@cli.command()
@click.option("--drive", "-d", default=None, help="Device path (auto-detect if omitted)")
def scan(drive: str | None) -> None:
    """Scan a DVD and display its titles."""
    from video_extractor.deps import check_handbrake
    from video_extractor.drive import DriveError, detect_disc
    from video_extractor.models import DiscInfo
    from video_extractor.scanner import ScanError, scan_disc
    from video_extractor.ui import show_disc_info, show_error, show_title_table

    # Check HandBrakeCLI
    hb = check_handbrake()
    if not hb.found:
        show_error("HandBrakeCLI not found. Install with: brew install handbrake")
        raise SystemExit(1)

    # Detect or use provided drive
    try:
        if drive:
            disc = DiscInfo(device_path=drive, mount_point=drive, volume_label="DVD")
        else:
            disc = detect_disc()
    except DriveError as e:
        show_error(str(e))
        raise SystemExit(1)

    show_disc_info(disc)

    # Scan
    try:
        dvd = scan_disc(disc)
    except ScanError as e:
        show_error(str(e))
        raise SystemExit(1)

    if not dvd.titles:
        show_error("No titles found on disc.")
        raise SystemExit(1)

    show_title_table(dvd)


@cli.command()
@click.option("--drive", "-d", default=None, help="Device path (auto-detect if omitted)")
@click.option("--output", "-o", default=".", type=click.Path(), help="Output directory")
@click.option(
    "--format", "-f", "fmt",
    type=click.Choice(["mkv", "mp4"], case_sensitive=False),
    default="mkv",
    help="Output container format",
)
@click.option(
    "--codec", "-c",
    type=click.Choice(["h264", "h265"], case_sensitive=False),
    default="h265",
    help="Video codec",
)
@click.option("--quality", "-q", type=click.IntRange(0, 51), default=20, help="RF quality (0-51)")
@click.option("--title", "-t", "title_num", type=int, default=None, help="Title number to rip")
@click.option("--main-feature", is_flag=True, help="Auto-select main feature title")
@click.option("--all-titles", is_flag=True, help="Rip all titles >1 minute")
@click.option("--audio-lang", default=None, help="Preferred audio language code (e.g. eng)")
@click.option("--subtitle-lang", default=None, help="Subtitle language to include (e.g. eng)")
def rip(
    drive: str | None,
    output: str,
    fmt: str,
    codec: str,
    quality: int,
    title_num: int | None,
    main_feature: bool,
    all_titles: bool,
    audio_lang: str | None,
    subtitle_lang: str | None,
) -> None:
    """Rip video from a DVD."""
    from video_extractor.deps import check_all
    from video_extractor.drive import DriveError, detect_disc
    from video_extractor.models import DiscInfo
    from video_extractor.ripper import RipError, rip_title
    from video_extractor.scanner import ScanError, scan_disc
    from video_extractor.ui import (
        console,
        create_progress,
        prompt_title_selection,
        show_completion,
        show_disc_info,
        show_error,
        show_title_table,
        show_warning,
    )

    # 1. Check dependencies
    deps = check_all()
    hb = next(d for d in deps if d.name == "HandBrakeCLI")
    dvdcss = next(d for d in deps if d.name == "libdvdcss")

    if not hb.found:
        show_error("HandBrakeCLI not found. Install with: brew install handbrake")
        raise SystemExit(1)
    if not dvdcss.found:
        show_warning("libdvdcss not found. For encrypted DVDs: brew install libdvdcss")

    # 2. Detect DVD
    try:
        if drive:
            disc = DiscInfo(device_path=drive, mount_point=drive, volume_label="DVD")
        else:
            disc = detect_disc()
    except DriveError as e:
        show_error(str(e))
        raise SystemExit(1)

    show_disc_info(disc)

    # 3. Scan disc
    console.print("[dim]Scanning disc...[/dim]")
    try:
        dvd = scan_disc(disc)
    except ScanError as e:
        show_error(str(e))
        raise SystemExit(1)

    if not dvd.titles:
        show_error("No titles found on disc.")
        raise SystemExit(1)

    show_title_table(dvd)

    # 4. Select titles
    if title_num is not None:
        title_map = {t.number: t for t in dvd.titles}
        if title_num not in title_map:
            show_error(f"Title {title_num} not found on disc.")
            raise SystemExit(1)
        selected = [title_map[title_num]]
    elif main_feature:
        selected = [t for t in dvd.titles if t.is_main_feature]
        if not selected:
            show_error("No main feature detected. Use --title to specify.")
            raise SystemExit(1)
    elif all_titles:
        selected = [t for t in dvd.titles if t.duration_seconds > 60]
        if not selected:
            show_error("No titles longer than 1 minute found.")
            raise SystemExit(1)
    else:
        selected = prompt_title_selection(dvd)

    console.print(
        f"\nRipping {len(selected)} title(s): "
        f"{', '.join(str(t.number) for t in selected)}\n"
    )

    # 5. Rip each title
    output_format = OutputFormat(fmt.lower())
    video_codec = VideoCodec(codec.lower())
    output_dir = Path(output)

    for title in selected:
        # Build output filename
        safe_label = "".join(
            c if c.isalnum() or c in "-_ " else "_"
            for c in disc.volume_label
        ).strip()
        filename = f"{safe_label}_t{title.number:02d}.{output_format.value}"
        out_path = output_dir / filename

        # Select audio tracks by language preference
        audio_selection = None
        if audio_lang and title.audio_tracks:
            matching = [
                a.index for a in title.audio_tracks
                if a.language.startswith(audio_lang)
            ]
            if matching:
                audio_selection = matching

        # Select subtitle tracks by language
        sub_selection = None
        if subtitle_lang and title.subtitle_tracks:
            matching = [
                s.index for s in title.subtitle_tracks
                if s.language.startswith(subtitle_lang)
            ]
            if matching:
                sub_selection = matching

        job = RipJob(
            title=title,
            source_device=disc.device_path,
            output_path=out_path,
            output_format=output_format,
            video_codec=video_codec,
            quality=quality,
            audio_tracks=audio_selection,
            subtitle_tracks=sub_selection,
        )

        # Encode with progress
        progress = create_progress()
        with progress:
            task_id = progress.add_task(
                f"Title {title.number} ({title.duration_display})",
                total=100,
            )

            def on_progress(pct: float, eta: str) -> None:
                progress.update(task_id, completed=pct)

            try:
                rip_title(job, on_progress=on_progress)
            except RipError as e:
                show_error(str(e))
                raise SystemExit(1)

        show_completion(out_path)

    if len(selected) > 1:
        console.print(f"\n[bold green]All {len(selected)} titles complete![/bold green]")
