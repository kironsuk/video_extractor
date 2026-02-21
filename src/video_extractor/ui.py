"""Rich-based terminal UI components."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.prompt import Prompt
from rich.table import Table

from video_extractor.deps import DepStatus
from video_extractor.models import DiscInfo, DVDInfo, Title

console = Console()


def show_dep_status(deps: list[DepStatus]) -> None:
    """Display dependency check results."""
    table = Table(title="Dependency Check")
    table.add_column("Tool", style="bold")
    table.add_column("Status")
    table.add_column("Path / Install")

    for dep in deps:
        if dep.found:
            status = "[green]Found[/green]"
            detail = dep.path or ""
        else:
            status = "[red]Missing[/red]"
            detail = f"[yellow]{dep.install_hint}[/yellow]"
        table.add_row(dep.name, status, detail)

    console.print(table)


def show_disc_info(disc: DiscInfo) -> None:
    """Display disc information in a panel."""
    console.print(Panel(
        f"[bold]{disc.volume_label}[/bold]\n"
        f"Device: {disc.device_path}\n"
        f"Mount:  {disc.mount_point}",
        title="DVD Disc",
    ))


def show_title_table(dvd: DVDInfo) -> None:
    """Display a table of all titles on the disc."""
    table = Table(title=f"Titles on {dvd.disc.volume_label}")
    table.add_column("#", style="bold", justify="right")
    table.add_column("Duration", justify="right")
    table.add_column("Chapters", justify="right")
    table.add_column("Resolution")
    table.add_column("Audio")
    table.add_column("Subtitles")
    table.add_column("Main", justify="center")

    for t in dvd.titles:
        audio_desc = ", ".join(
            f"{a.language}({a.channels}ch)" for a in t.audio_tracks
        ) or "-"
        sub_desc = ", ".join(
            s.language for s in t.subtitle_tracks
        ) or "-"
        main = "[green]*[/green]" if t.is_main_feature else ""

        style = "bold" if t.is_main_feature else None
        table.add_row(
            str(t.number),
            t.duration_display,
            str(len(t.chapters)),
            t.resolution or "-",
            audio_desc,
            sub_desc,
            main,
            style=style,
        )

    console.print(table)


def prompt_title_selection(dvd: DVDInfo) -> list[Title]:
    """Interactively prompt the user to select titles to rip.

    Supports:
    - A single title number: "1"
    - Multiple titles: "1,3,5"
    - "main" to select the main feature
    - "all" to select all titles >1 minute
    """
    main_titles = [t for t in dvd.titles if t.is_main_feature]

    hint_parts = ["Enter title number(s)"]
    if main_titles:
        main_nums = ", ".join(str(t.number) for t in main_titles)
        hint_parts.append(f'"main" for main feature (title {main_nums})')
    hint_parts.append('"all" for all titles >1 min')

    prompt_text = " | ".join(hint_parts)

    while True:
        choice = Prompt.ask(f"\n[bold]{prompt_text}[/bold]")
        choice = choice.strip().lower()

        if choice == "main":
            if main_titles:
                return main_titles
            console.print("[yellow]No main feature detected. Pick a title number.[/yellow]")
            continue

        if choice == "all":
            long_titles = [t for t in dvd.titles if t.duration_seconds > 60]
            if long_titles:
                return long_titles
            console.print("[yellow]No titles longer than 1 minute found.[/yellow]")
            continue

        # Parse comma-separated numbers
        try:
            numbers = [int(n.strip()) for n in choice.split(",")]
        except ValueError:
            console.print("[red]Invalid input. Enter title numbers, 'main', or 'all'.[/red]")
            continue

        title_map = {t.number: t for t in dvd.titles}
        selected = []
        invalid = []
        for n in numbers:
            if n in title_map:
                selected.append(title_map[n])
            else:
                invalid.append(n)

        if invalid:
            console.print(f"[red]Unknown title(s): {invalid}[/red]")
            continue

        if selected:
            return selected

        console.print("[red]No titles selected.[/red]")


def create_progress() -> Progress:
    """Create a Rich progress bar for encoding."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    )


def show_completion(output_path: Path) -> None:
    """Show a completion message with file info."""
    size_mb = output_path.stat().st_size / (1024 * 1024)
    console.print(Panel(
        f"[bold green]Done![/bold green]\n"
        f"Output: {output_path}\n"
        f"Size:   {size_mb:.1f} MB",
        title="Complete",
    ))


def show_error(message: str) -> None:
    """Display an error message."""
    console.print(f"[bold red]Error:[/bold red] {message}")


def show_warning(message: str) -> None:
    """Display a warning message."""
    console.print(f"[yellow]Warning:[/yellow] {message}")
