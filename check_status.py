import argparse
from pathlib import Path
from rich.console import Console  # type: ignore
from rich.table import Table  # type: ignore

console = Console()


def _find_input_subfolder(incomplete_stems: list[str], input_dir: Path) -> Path:
    """Find the most specific input subfolder containing the incomplete videos."""
    media_exts = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".mp3", ".wav", ".m4a", ".flac"}

    parents: set[Path] = set()
    for stem in incomplete_stems:
        for f in input_dir.rglob("*"):
            if f.stem == stem and f.suffix.lower() in media_exts:
                parents.add(f.parent)
                break

    if not parents:
        return input_dir
    if len(parents) == 1:
        return next(iter(parents))

    # Find the common ancestor of all parent dirs (within input_dir)
    parts_list = [p.parts for p in parents]
    min_len = min(len(p) for p in parts_list)
    common_parts = []
    for i in range(min_len):
        if all(p[i] == parts_list[0][i] for p in parts_list):
            common_parts.append(parts_list[0][i])
        else:
            break
    common = Path(*common_parts) if common_parts else input_dir
    # Don't go above input_dir
    try:
        common.relative_to(input_dir)
        return common
    except ValueError:
        return input_dir


def main():
    parser = argparse.ArgumentParser(description="Check the processing status of all videos in the output directory.")
    parser.add_argument("--dir", type=Path, default=Path("output"), help="Path to the output directory to check")
    parser.add_argument("--input", type=Path, default=Path("input"), help="Path to the input directory (used to generate Step 2 command)")
    args = parser.parse_args()

    output_dir = args.dir
    if not output_dir.exists() or not output_dir.is_dir():
        console.print(f"[bold red]Output directory '{output_dir}' not found.[/bold red]")
        return
        
    table = Table(title="Subtitle Forge - Processing Status")
    table.add_column("Video Name", style="cyan")
    table.add_column("ASR (subtitle.srt)", justify="center")
    table.add_column("Transcript", justify="center")
    table.add_column("Translation", justify="center")
    table.add_column("Bilingual", justify="center")
    table.add_column("Study Notes", justify="center")
    table.add_column("Status", style="bold")
    
    # Check all subdirectories
    dirs = [d for d in output_dir.iterdir() if d.is_dir()]
    dirs.sort(key=lambda x: x.name)
    
    total_issues = 0
    incomplete_stems: list[str] = []

    for d in dirs:
        has_asr = (d / f"{d.name}.srt").exists()
        has_txt = (d / f"{d.name}.transcript.txt").exists()
        has_zh = (d / f"{d.name}.zh.srt").exists()
        has_bi = (d / f"{d.name}.bilingual.srt").exists()
        has_notes = (d / f"{d.name}.studynotes.md").exists()
        
        # Check for debug files indicating failure
        has_debug = (d / f"{d.name}_asr_debug.txt").exists()
        
        row = [
            d.name,
            "[green]✓[/green]" if has_asr else ("[bold red]✗ (Debug)[/bold red]" if has_debug else "[red]✗[/red]"),
            "[green]✓[/green]" if has_txt else "[red]✗[/red]",
            "[green]✓[/green]" if has_zh else "[yellow]?[/yellow]",
            "[green]✓[/green]" if has_bi else "[red]✗[/red]",
            "[green]✓[/green]" if has_notes else "[red]✗[/red]",
        ]
        
        # Determine overall status
        if has_asr and has_txt and has_zh and has_bi and has_notes:
            status = "[green]Complete[/green]"
        elif has_debug and not has_asr:
            status = "[bold red]FAILED (ASR Error)[/bold red]"
            total_issues += 1
            incomplete_stems.append(d.name)
        elif has_asr and (not has_zh or not has_bi):
            status = "[yellow]Interrupted (Translation)[/yellow]"
            total_issues += 1
            incomplete_stems.append(d.name)
        else:
            status = "[red]Incomplete[/red]"
            total_issues += 1
            incomplete_stems.append(d.name)
            
        row.append(status)
        table.add_row(*row)
        
    console.print(table)
    
    if total_issues > 0:
        console.print(f"\n[bold yellow]Found {total_issues} videos with incomplete processing.[/bold yellow]")
        console.print("\n[bold cyan]Step 1 — Auto-fix local gaps (no API cost):[/bold cyan]")
        console.print("  ./venv/bin/python3 recover.py")
        console.print("\n[bold cyan]Step 2 — Complete remaining with API:[/bold cyan]")
        input_path = _find_input_subfolder(incomplete_stems, args.input)
        # If input_path is deep, also suggest the parent 'input/' for processing all batches
        main_cmd = f"./venv/bin/python3 main.py {input_path}/ --language English"
        console.print(f"  {main_cmd}")
        if str(input_path) != "input":
            console.print(f"  [dim]Or run: ./venv/bin/python3 main.py input/ --language English (to scan all batches)[/dim]\n")
        else:
            console.print("")
    else:
        console.print("\n[bold green]All videos appear to be fully processed![/bold green]")

if __name__ == "__main__":
    main()
