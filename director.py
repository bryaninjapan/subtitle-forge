#!/usr/bin/env python3
"""CLI entry point for the Multi-Agent Orchestration Engine.

This file is kept as a thin entry point after the refactoring in
director/engine.py and director/state_store.py.
"""
import argparse
from pathlib import Path

from rich.console import Console  # type: ignore

from config import BASE_DIR, INPUT_DIR  # type: ignore
from asr_engine import is_media_file  # type: ignore
from director.engine import WorkflowEngine

console = Console()


def main():
    workflow_json = BASE_DIR / "multi_agent_workflow.json"
    if not workflow_json.exists():
        console.print("[bold red]ERROR:[/bold red] multi_agent_workflow.json not found.")
        return

    parser = argparse.ArgumentParser()
    parser.add_argument("paths", type=Path, nargs="*", help="Paths to media files or directories.")
    parser.add_argument("--language", "-l", help="Source language.")
    parser.add_argument("--style", default="academic", help="Translation style.")
    args = parser.parse_args()

    if args.paths:
        media_files = []
        for p in args.paths:
            if p.is_file() and is_media_file(p):
                media_files.append(p)
            elif p.is_dir():
                media_files.extend([f for f in p.rglob("*") if is_media_file(f)])
    else:
        media_files = [f for f in INPUT_DIR.rglob("*") if is_media_file(f)]

    if not media_files:
        console.print("[yellow]No media files found to process.[/yellow]")
        return

    engine = WorkflowEngine(workflow_json, language=args.language, style=args.style)
    engine.run_all(media_files)


if __name__ == "__main__":
    main()
