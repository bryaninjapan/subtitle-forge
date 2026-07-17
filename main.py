#!/usr/bin/env python3
"""
main.py — The Primary Entry Point for Subtitle Forge.
Now fully integrated with the Multi-Agent Orchestration Engine (director.py).
"""

import argparse
import json
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


def send_notification(title: str, message: str) -> None:
    """Send a macOS desktop notification. Uses osascript (built-in) or terminal-notifier if available."""
    import shutil, subprocess

    if shutil.which("terminal-notifier"):
        try:
            subprocess.run(
                ["terminal-notifier", "-title", title, "-message", message, "-sound", "default"],
                timeout=5, capture_output=True,
            )
            return
        except (subprocess.TimeoutExpired, OSError):
            pass

    # Fallback: osascript (built-in on macOS)
    try:
        subprocess.run(
            ["osascript", "-e", f'display notification "{message}" with title "{title}"'],
            timeout=5, capture_output=True,
        )
    except (subprocess.TimeoutExpired, OSError):
        pass  # Silently fail — notification is non-critical

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

def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser (extracted for testability)."""
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
    parser.add_argument("--interactive", "-i", action="store_true", help="Launch interactive mode with guided prompts.")
    parser.add_argument("--completion", choices=["zsh", "bash"], help="Generate shell completion script and print to stdout.")
    parser.add_argument("--no-notify", action="store_true", help="Suppress desktop notification on completion.")
    parser.add_argument("--script", type=Path, help="Path to reference transcript for script matching (uses ForcedAligner alignment).")
    parser.add_argument("--burn", action="store_true", help="Burn subtitles into video after processing.")
    parser.add_argument("--burn-font-size", type=int, default=24, help="Font size for burned subtitles (default: 24).")
    return parser


def generate_completion(shell: str) -> None:
    """Print shell completion script for zsh or bash to stdout."""
    if shell == "zsh":
        print(r'''#compdef _subtitle_forge subtitle_forge main.py

typeset -A _sf_commands
_sf_commands=(
  paths   "file"
  --language   "string"
  -l           "string"
  --style      "academic casual exam-focused"
  --server     "flag"
  --watch      "flag"
  --wipe       "flag"
  --dry-run    "flag"
  --chapters   "flag"
  --no-chapters "flag"
  --interactive "flag"
  -i           "flag"
  --completion "zsh bash"
  --help       "flag"
)

typeset -A _sf_languages
_sf_languages=(
  "zh"   "Chinese"
  "en"   "English"
  "ja"   "Japanese"
  "ko"   "Korean"
  "fr"   "French"
  "de"   "German"
  "es"   "Spanish"
  "pt"   "Portuguese"
  "ru"   "Russian"
  "ar"   "Arabic"
  "th"   "Thai"
  "vi"   "Vietnamese"
)

_subtitle_forge() {
  local curcontext="$curcontext" state line ret=1
  _arguments -C \
    '(- *)--help[Show help message]' \
    '--language[Source language hint]:language:->langs' \
    '-l[Source language hint]:language:->langs' \
    '--style[Translation style]:style:(academic casual exam-focused)' \
    '--server[Launch Web Dashboard]' \
    '--watch[Monitor input directory]' \
    '--wipe[Wipe output directory]' \
    '--dry-run[Preview without APIs]' \
    '--chapters[Generate chapter timestamps]' \
    '--no-chapters[Skip chapter generation]' \
    '--interactive[Guided interactive mode]' \
    '-i[Guided interactive mode]' \
    '--completion[Generate completion script]:shell:(zsh bash)' \
    '*:media file:_files -g "*.(${(j:|:)${(s: :)_media_exts:-mp4 mkv mov avi m4v webm mp3 wav m4a aac}})"' \
    && ret=0

  case "$state" in
    langs)
      _describe -t languages "language" _sf_languages && ret=0
      ;;
  esac
  return ret
}

_subtitle_forge "$@"
''')
    elif shell == "bash":
        print(r'''_subtitle_forge_completion() {
  local cur prev opts lang_opts style_opts
  COMPREPLY=()
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"

  opts="--help --language -l --style --server --watch --wipe --dry-run --chapters --no-chapters --interactive -i --completion"
  lang_opts="zh en ja ko fr de es pt ru ar th vi"
  style_opts="academic casual exam-focused"
  shell_opts="zsh bash"

  case "${prev}" in
    --language|-l)
      COMPREPLY=( $(compgen -W "${lang_opts}" -- "${cur}") )
      return 0
      ;;
    --style)
      COMPREPLY=( $(compgen -W "${style_opts}" -- "${cur}") )
      return 0
      ;;
    --completion)
      COMPREPLY=( $(compgen -W "${shell_opts}" -- "${cur}") )
      return 0
      ;;
  esac

  # Complete file paths if no option prefix
  if [[ ${cur} == -* ]]; then
    COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
  else
    COMPREPLY=( $(compgen -f -- "${cur}") )
  fi
  return 0
}
complete -F _subtitle_forge_completion main.py subtitle_forge
''')


def interactive_mode(no_notify: bool = False) -> None:
    """Run in interactive mode: guided prompts for files, language, style, chapters."""
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich import box

    console.print()
    console.print(Panel.fit(
        "[bold cyan]Subtitle Forge — Interactive Mode[/bold cyan]\n"
        "[dim]Guided subtitle processing for CFA videos[/dim]",
        border_style="cyan",
    ))
    console.print()

    # 1. Collect file paths (comma-separated, or enter for input/)
    paths_raw = Prompt.ask(
        "[bold]📁 Input files[/bold]  (drag paths here or type comma-separated, "
        "[dim]enter=use input/[/dim])",
        default="",
    )
    media_files: list[Path] = []
    if paths_raw.strip():
        for part in paths_raw.replace(",", " ").split():
            p = Path(part.strip().strip('"').strip("'"))
            if p.is_file() and is_media_file(p):
                media_files.append(p)
            elif p.is_dir():
                media_files.extend(f for f in p.rglob("*") if is_media_file(f))
            else:
                console.print(f"  [dim red]✗ Skipped (not found or not media): {p}[/dim red]")
    else:
        media_files = [f for f in INPUT_DIR.rglob("*") if is_media_file(f)]

    if not media_files:
        console.print("[bold red]No media files found. Exiting.[/bold red]")
        return

    # 2. Language
    lang = Prompt.ask("[bold]🌐 Language[/bold]", default="", show_default=False)
    language = lang.strip() or None

    # 3. Style
    style = Prompt.ask(
        "[bold]🎨 Style[/bold]",
        choices=["academic", "casual", "exam-focused"],
        default="academic",
    )

    # 4. Chapters
    chapters = Confirm.ask("[bold]📑 Generate chapters?[/bold]", default=True)

    # 5. Summary table
    console.print()
    table = Table(box=box.SIMPLE_HEAD, title="[bold]Execution Plan[/bold]")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    table.add_row("Files", f"{len(media_files)} file(s)")
    for f in media_files[:5]:
        table.add_row("", f"  • {f.name}")
    if len(media_files) > 5:
        table.add_row("", f"  … and {len(media_files) - 5} more")
    table.add_row("Language", language or "auto-detect")
    table.add_row("Style", style)
    table.add_row("Chapters", "yes" if chapters else "no")
    console.print(table)
    console.print()

    if not Confirm.ask("[bold]🚀 Proceed?[/bold]", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    # 6. Execute
    console.print()
    engine = WorkflowEngine(
        BASE_DIR / "multi_agent_workflow.json",
        language=language,
        style=style,
        chapters=chapters,
    )
    engine.run_all(media_files)
    print_summary()
    if not no_notify:
        send_notification("Subtitle Forge", f"Done! {len(media_files)} file(s) processed.")


def main():
    parser = build_parser()
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

    # 3. Interactive Mode
    if args.interactive:
        interactive_mode(no_notify=args.no_notify)
        return

    # 4. Completion Mode
    if args.completion:
        generate_completion(args.completion)
        return

    # 5. Load reference script (if provided)
    reference_text: str | None = None
    if args.script:
        if args.script.exists():
            reference_text = args.script.read_text(encoding="utf-8")
            console.print(f"[bold green]Loaded reference script:[/bold green] {args.script.name} ({len(reference_text.split())} words)")
        else:
            console.print(f"[bold red]Script file not found:[/bold red] {args.script}")
            return

    # 6. Initialize Engine
    workflow_json = BASE_DIR / "multi_agent_workflow.json"
    engine = WorkflowEngine(workflow_json, language=args.language, style=args.style, chapters=args.chapters)

    # 5. Watch Mode
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

    # 6. Batch Run
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
        # When --script is used, call transcribe_files directly for script matching
        if reference_text:
            from asr_engine import transcribe_files  # type: ignore
            results = transcribe_files(media_files, language=args.language, reference_text=reference_text)
            console.print(f"[bold green]Script matching applied to {len(results)} file(s)[/bold green]")
        else:
            engine.run_all(media_files)
        print_summary()

        # Batch burn-in subtitles
        if args.burn and media_files:
            from srt_burn import batch_burn  # type: ignore
            console.print(f"\n[bold cyan]Burning subtitles for {len(media_files)} video(s)...[/bold cyan]")
            burned = batch_burn(
                media_files,
                subtitle_search_dirs=[OUTPUT_DIR],
                output_dir=BASE_DIR / "burned",
                font_size=args.burn_font_size,
            )
            console.print(f"[bold green]Burn complete: {len(burned)}/{len(media_files)} video(s)[/bold green]")

        if not args.no_notify:
            send_notification("Subtitle Forge", f"Done! {len(media_files)} file(s) processed.")
        
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
