#!/usr/bin/env python3
"""
main.py — The Primary Entry Point for Subtitle Forge.
Now fully integrated with the Multi-Agent Orchestration Engine (director.py).
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from rich.console import Console # type: ignore
from rich.panel import Panel # type: ignore
from watchdog.observers import Observer # type: ignore
from watchdog.events import FileSystemEventHandler # type: ignore

# Internal imports
from config import BASE_DIR, INPUT_DIR, OUTPUT_DIR, VIDEO_EXTENSIONS, AUDIO_EXTENSIONS # type: ignore
from asr_engine import is_media_file # type: ignore
from usage_tracker import get_total_usage # type: ignore
from director import WorkflowEngine # type: ignore

console = Console()

class WatchHandler(FileSystemEventHandler):
    def __init__(self, engine: WorkflowEngine):
        self.engine = engine
        self.processing = set()

    def on_created(self, event):
        if not event.is_directory and is_media_file(Path(event.src_path)):
            p = Path(event.src_path)
            if p not in self.processing:
                self.processing.add(p)
                console.print(f"\n[bold green][Watch][/bold green] Detected new file: {p.name}")
                time.sleep(2)  # Give it a moment to finish writing
                self.engine.run_all([p])
                self.processing.remove(p)

def print_summary():
    """Prints cost summary and logs to history."""
    totals = get_total_usage()
    cost_str = f"Total Session/All-time Cost: ${totals.get('cost', 0.0):.4f}"
    console.print(Panel(f"[bold green]{cost_str}[/bold green]", title="Financial Summary", expand=False))
    
    try:
        from datetime import datetime
        log_file = BASE_DIR / "cost_history.md"
        if not log_file.exists():
            log_file.write_text("# Subtitle Forge - Cost History\n\n| Date | Time | Cost |\n| :--- | :--- | :--- |\n", encoding="utf-8")
        
        now = datetime.now().strftime("%Y-%m-%d | %H:%M:%S")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"| {now} | ${totals.get('cost', 0.0):.4f} |\n")
    except Exception as e:
        console.print(f"[dim red]Failed to log cost history: {e}[/dim red]")

def main():
    parser = argparse.ArgumentParser(description="Subtitle Forge - Multi-Agent AI Subtitling & Study System")
    parser.add_argument("paths", type=Path, nargs="*", help="Paths to media files or directories.")
    parser.add_argument("--language", "-l", help="Source language hint.")
    parser.add_argument("--style", default="academic", help="Translation style (academic, casual, exam-focused).")
    parser.add_argument("--server", action="store_true", help="Launch the Web Dashboard.")
    parser.add_argument("--watch", action="store_true", help="Monitor input directory for new files.")
    parser.add_argument("--wipe", action="store_true", help="Wipe output directory and start fresh.")
    parser.add_argument("--dry-run", action="store_true", help="Preview files to process without calling any APIs.")
    parser.add_argument("--chapters", dest="chapters", action="store_true", default=True, help="Generate chapter timestamps (default: on).")
    parser.add_argument("--no-chapters", dest="chapters", action="store_false", help="Skip chapter generation.")
    args = parser.parse_args()

    # 1. Cleanup
    if args.wipe:
        import shutil
        if OUTPUT_DIR.exists():
            console.print("[bold red]Wiping output directory...[/bold red]")
            shutil.rmtree(OUTPUT_DIR)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        return

    # 2. Server Mode
    if args.server:
        from server import app # type: ignore
        console.print("[bold cyan]Launching Web Dashboard...[/bold cyan]")
        app.run(port=5000)
        return

    # 3. Initialize Engine
    workflow_json = BASE_DIR / "multi_agent_workflow.json"
    engine = WorkflowEngine(workflow_json, language=args.language, style=args.style, chapters=args.chapters)

    # 4. Watch Mode
    if args.watch:
        console.print(f"[bold magenta]Watcher active on {INPUT_DIR}[/bold magenta]")
        observer = Observer()
        observer.schedule(WatchHandler(engine), str(INPUT_DIR), recursive=False)
        observer.start()
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
        return

    # 5. Batch Run
    media_files = []
    if args.paths:
        for p in args.paths:
            if p.is_file() and is_media_file(p): media_files.append(p)
            elif p.is_dir(): media_files.extend([f for f in p.rglob("*") if is_media_file(f)])
    else:
        media_files = [f for f in INPUT_DIR.rglob("*") if is_media_file(f)]

    if args.dry_run:
        console.print("[bold yellow][DRY RUN] Files that would be processed:[/bold yellow]")
        for f in media_files:
            console.print(f"  • {f.name}")
        console.print(f"\n[dim]Total: {len(media_files)} file(s). No APIs called.[/dim]")
        return

    if media_files:
        engine.run_all(media_files)
        print_summary()
        
        # Anki Export
        from config import GLOSSARY_PATH # type: ignore
        if GLOSSARY_PATH.exists():
            from anki_exporter import export_to_anki # type: ignore
            try:
                export_to_anki(json.loads(GLOSSARY_PATH.read_text(encoding="utf-8")), BASE_DIR / "cfa_glossary.apkg")
                console.print("[bold green]Anki deck updated: cfa_glossary.apkg[/bold green]")
            except Exception as e:
                console.print(f"[dim red]Anki export failed: {e}[/dim red]")
    else:
        console.print("[yellow]No media files found to process. Use -h for help.[/yellow]")

if __name__ == "__main__":
    main()
