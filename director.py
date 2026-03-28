#!/usr/bin/env python3
"""
director.py — The Multi-Agent Orchestration Engine for Subtitle Forge.

This engine parses multi_agent_workflow.json and executes a Directed Acyclic Graph (DAG)
of specialized agents on media files.
"""

import json
import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from rich.console import Console # type: ignore
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TaskID # type: ignore
from rich.panel import Panel # type: ignore
from rich.table import Table # type: ignore

# Internal imports
from config import BASE_DIR, INPUT_DIR, OUTPUT_DIR, VIDEO_EXTENSIONS, AUDIO_EXTENSIONS # type: ignore
from media_utils import get_file_hash # type: ignore
from asr_engine import is_media_file # type: ignore

console = Console()

@dataclass
class AgentConfig:
    id: str
    role: str
    action: str
    inputs: List[str]
    outputs: List[str]
    dependencies: List[str]
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    run_condition: Optional[str] = None

class StateStore:
    """Manages persistence of agent states in the working directory."""
    def __init__(self, working_dir: Path):
        self.path = working_dir / "state.json"
        self.working_dir = working_dir
        self.lock = threading.Lock()
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try: return json.loads(self.path.read_text(encoding="utf-8"))
            except: pass
        return {"agents": {}, "outputs": {}}

    def save(self):
        with self.lock:
            self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_agent_status(self, agent_id: str) -> str:
        return self.data["agents"].get(agent_id, {}).get("status", "PENDING")

    def set_agent_status(self, agent_id: str, status: str, error: Optional[str] = None):
        if agent_id not in self.data["agents"]: self.data["agents"][agent_id] = {}
        self.data["agents"][agent_id]["status"] = status
        self.data["agents"][agent_id]["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if error: 
            self.data["agents"][agent_id]["error"] = error
        elif status in ["RUNNING", "COMPLETED"]:
            self.data["agents"][agent_id].pop("error", None)
        self.save()

    def update_outputs(self, outputs: Dict[str, Any]):
        # Ensure all types are JSON serializable
        def serialize(v):
            if isinstance(v, (list, tuple)): return [serialize(i) for i in v]
            if isinstance(v, dict): return {k: serialize(val) for k, val in v.items()}
            if isinstance(v, Path): return str(v)
            return v
        
        self.data["outputs"].update({k: serialize(v) for k, v in outputs.items()})
        self.save()

    def get_output(self, key: str) -> Any:
        # Check explicit outputs first
        if key in self.data["outputs"]: return self.data["outputs"][key]
        # Some special keys map to working dir
        if key == "working_directory": return str(self.working_dir)
        return None

class WorkflowEngine:
    def __init__(self, workflow_path: Path, language: Optional[str] = None, style: str = "academic", chapters: bool = True):
        self.workflow_path = workflow_path
        self.language = language
        self.style = style
        self.chapters = chapters
        self.workflow = self._load_workflow()
        self.agents = []
        for a in self.workflow.get("agents", []):
            self.agents.append(AgentConfig(
                id=str(a.get("id")),
                role=str(a.get("role")),
                action=str(a.get("action")),
                inputs=list(a.get("inputs", [])),
                outputs=list(a.get("outputs", [])),
                dependencies=list(a.get("dependencies", [])),
                retry_policy=dict(a.get("retry_policy", {})),
                run_condition=a.get("run_condition")
            ))
        self.agent_map = {a.id: a for a in self.agents}
        # Track working dirs where translation actually ran this session (not bootstrapped)
        self.session_translated: List[Path] = []
        self._session_lock = threading.Lock()

    def _load_workflow(self) -> Dict[str, Any]:
        return json.loads(self.workflow_path.read_text(encoding="utf-8"))

    def _bootstrap_from_disk(self, state: StateStore, stem: str):
        """Checks if expected output files exist and marks agents as COMPLETED.

        Outputs are always restored from disk when files exist, regardless of whether
        the agent is already marked COMPLETED — this prevents silent failures caused by
        a COMPLETED status with missing outputs (e.g. after state.json migration).
        """
        w_d = state.working_dir

        # 0. Preflight — mark COMPLETED if the 16kHz wav already exists so the
        #    engine skips re-extracting audio on every run.
        wav_p = w_d / f"{stem}_16k.wav"
        if wav_p.exists():
            if state.get_agent_status("preflight_agent") != "COMPLETED":
                state.set_agent_status("preflight_agent", "COMPLETED")
            # Always ensure audio_16khz_path output is present
            if not state.get_output("audio_16khz_path"):
                state.update_outputs({"audio_16khz_path": str(wav_p)})

        # 1. ASR — only requires .srt; .transcript.txt used as richer fallback.
        srt_p = w_d / f"{stem}.srt"
        txt_p = w_d / f"{stem}.transcript.txt"
        if srt_p.exists():
            if state.get_agent_status("asr_agent") != "COMPLETED":
                state.set_agent_status("asr_agent", "COMPLETED")
            # Always restore outputs so downstream agents are never starved
            if not state.get_output("raw_srt_text"):
                raw_srt = srt_p.read_text(encoding="utf-8")
                transcript_text = txt_p.read_text(encoding="utf-8") if txt_p.exists() else raw_srt
                state.update_outputs({
                    "raw_srt_text": raw_srt,
                    "transcript_text": transcript_text,
                    "srt_path": str(srt_p)
                })

        # 2. Translation
        zh_srt_p = w_d / f"{stem}.zh.srt"
        if zh_srt_p.exists():
            if state.get_agent_status("translation_agent") != "COMPLETED":
                state.set_agent_status("translation_agent", "COMPLETED")
            if not state.get_output("zh_srt_text"):
                state.update_outputs({"zh_srt_text": zh_srt_p.read_text(encoding="utf-8")})

        # 3. Bilingual
        bi_srt_p = w_d / f"{stem}.bilingual.srt"
        if bi_srt_p.exists():
            if state.get_agent_status("bilingual_agent") != "COMPLETED":
                state.set_agent_status("bilingual_agent", "COMPLETED")

        # 4. Vision
        frames_dir = w_d / "frames"
        if frames_dir.exists() and any(frames_dir.glob("*.jpg")):
            if state.get_agent_status("vision_agent") != "COMPLETED":
                state.set_agent_status("vision_agent", "COMPLETED")
            if not state.get_output("frame_paths"):
                state.update_outputs({
                    "frame_paths": [str(p) for p in sorted(frames_dir.glob("*.jpg"))],
                    "visual_context_summary": ""
                })

        # 5. Study Notes
        notes_p = w_d / f"{stem}.studynotes.md"
        if notes_p.exists():
            if state.get_agent_status("study_notes_agent") != "COMPLETED":
                state.set_agent_status("study_notes_agent", "COMPLETED")

        # 6. Chapters
        chapters_p = w_d / f"{stem}.chapter.txt"
        if chapters_p.exists():
            if state.get_agent_status("chapter_agent") != "COMPLETED":
                state.set_agent_status("chapter_agent", "COMPLETED")

        # 7. QA Judge — mark COMPLETED if translation already exists so the judge
        #    does not re-score translations on every pipeline re-run.
        if zh_srt_p.exists():
            if state.get_agent_status("qa_judge_agent") != "COMPLETED":
                state.set_agent_status("qa_judge_agent", "COMPLETED")
                state.update_outputs({"qa_score": None, "qa_critique": "(bootstrapped — skipped re-scoring)"})

    def process_video(self, video_path: Path, progress: Progress, parent_task_id: TaskID):
        """Processes a single video through the DAG."""
        working_dir = OUTPUT_DIR / video_path.stem
        working_dir.mkdir(parents=True, exist_ok=True)
        
        state = StateStore(working_dir)
        
        # Check if video has changed via hash
        from media_utils import get_file_hash # type: ignore
        current_hash = get_file_hash(video_path)
        last_hash = state.data.get("video_hash")
        
        if last_hash and last_hash != current_hash:
            console.print(f"[yellow]Video {video_path.name} has changed. Resetting state...[/yellow]")
            state.data = {"agents": {}, "outputs": {}, "video_hash": current_hash}
            state.save()
        else:
            state.data["video_hash"] = current_hash
            self._bootstrap_from_disk(state, video_path.stem)

        # Initial global inputs
        initial_context: Dict[str, Any] = {"video_path": str(video_path), "style": self.style}
        if self.language: initial_context["language"] = str(self.language)
        state.update_outputs(initial_context)
        
        # Local task for this video
        v_name = str(video_path.name)
        video_task = progress.add_task(f" [dim]{v_name[:30]}[/dim]", total=len(self.agents)) # type: ignore
        
        # Track completed agents for this video run
        completed_agents: Set[str] = {id for id, info in state.data["agents"].items() if info["status"] == "COMPLETED"}
        failed_agents: Set[str] = {id for id, info in state.data["agents"].items() if info["status"] == "FAILED"}
        progress.advance(video_task, advance=len(completed_agents))

        while len(completed_agents) + len(failed_agents) < len(self.agents):
            # Find agents ready to run: deps met (all completed), not already done/failed,
            # and not blocked by a failed upstream agent (transitively)
            def is_blocked(agent_id: str, visited: set | None = None) -> bool:
                if visited is None: visited = set()
                if agent_id in visited: return False
                visited.add(agent_id)
                a = self.agent_map.get(agent_id)
                if a is None: return False
                return any(dep in failed_agents or is_blocked(dep, visited) for dep in a.dependencies)

            ready_agents = [
                a for a in self.agents
                if a.id not in completed_agents
                and all(dep in completed_agents for dep in a.dependencies)
                and not is_blocked(a.id)
            ]

            if not ready_agents:
                # All remaining agents are either done, failed, or blocked by failures
                if failed_agents:
                    v_name = str(video_path.name)
                    progress.update(video_task, description=f" {v_name[:30]} [red]Partial ({len(failed_agents)} failed)[/red]") # type: ignore
                break

            # Execute ready agents — independent branches run in the same round
            for agent in ready_agents:
                success = self.execute_agent(agent, state, progress, video_task)
                if success:
                    completed_agents.add(agent.id)
                    progress.advance(video_task)
                else:
                    # Mark failed and continue — sibling branches are NOT cancelled
                    failed_agents.add(agent.id)
        
        v_name = str(video_path.name)
        if failed_agents:
            progress.update(video_task, description=f" {v_name[:30]} [yellow]Partial ({len(failed_agents)} failed)[/yellow]") # type: ignore
            return False
        progress.update(video_task, description=f" {v_name[:30]} [green]Complete[/green]") # type: ignore
        return True

    def execute_agent(self, agent: AgentConfig, state: StateStore, progress: Progress, task_id: TaskID) -> bool:
        """Dispatches an agent action to the corresponding module."""
        state.set_agent_status(agent.id, "RUNNING")
        v_name = str(state.working_dir.name)
        progress.update(task_id, description=f" {v_name[:30]} [cyan]{agent.id}...[/cyan]") # type: ignore
        
        max_retries = int(agent.retry_policy.get("max_retries", 0) or 0)
        delay_seconds: float = float(agent.retry_policy.get("delay_seconds", agent.retry_policy.get("base_delay_seconds", 5)) or 5.0) # type: ignore
        backoff_multiplier: float = float(agent.retry_policy.get("backoff_multiplier", 1.0) or 1.0) # type: ignore
        
        attempts = 0
        last_error = ""
        while attempts <= max_retries:
            try:
                # Map action to actual implementation
                result_outputs = self._dispatch_action(agent, state)

                # Mark COMPLETED before persisting outputs so that a force-kill
                # between these two calls leaves state.json with COMPLETED status.
                # _bootstrap_from_disk will restore any missing outputs from disk
                # files (e.g. .srt, .zh.srt) on the next run.
                state.set_agent_status(agent.id, "COMPLETED")
                if agent.id == "translation_agent":
                    with self._session_lock:
                        self.session_translated.append(state.working_dir)
                state.update_outputs(result_outputs)
                return True
            except Exception as e:
                attempts += 1
                last_error = str(e)
                if attempts <= max_retries:
                    progress.update(task_id, description=f" {v_name[:30]} [yellow]{agent.id} (Retry {attempts}/{max_retries})[/yellow]") # type: ignore
                    console.print(f"[yellow]Agent {agent.id} failed on {state.working_dir.name}, retrying in {delay_seconds}s: {e}[/yellow]")
                    time.sleep(delay_seconds)
                    delay_seconds *= backoff_multiplier # type: ignore

        state.set_agent_status(agent.id, "FAILED", error=last_error)
        console.print(f"[bold red]Agent {agent.id} failed on {state.working_dir.name} after {max_retries} retries:[/bold red] {last_error}")
        return False

    def _dispatch_action(self, agent: AgentConfig, state: StateStore) -> Dict[str, Any]:
        """Maps agent.action to actual Python function calls."""
        action = agent.action
        
        # Collect inputs from state store
        inputs = {key: state.get_output(key) for key in agent.inputs}
        
        if action == "extract_audio_and_validate":
            from preflight_agent import extract_audio_and_validate # type: ignore
            return extract_audio_and_validate(**inputs)
            
        elif action == "transcribe_audio":
            from asr_engine import transcribe_one_video # type: ignore
            return transcribe_one_video(**inputs)
            
        elif action == "translate_srt":
            from translator import translate_one_video # type: ignore
            return translate_one_video(**inputs)
            
        elif action == "create_bilingual_srt":
            from srt_utils import create_bilingual_srt_from_text # type: ignore
            return create_bilingual_srt_from_text(**inputs)
            
        elif action == "extract_keyframes":
            from vision_engine import extract_keyframes # type: ignore
            return {
                "frame_paths": extract_keyframes(Path(inputs["video_path"]), Path(inputs["working_directory"])),
                "visual_context_summary": "" # Placeholder for future vision analysis
            }
            
        elif action == "generate_study_notes":
            from notes_generator import generate_study_notes # type: ignore
            raw_fps = inputs["frame_paths"]
            frame_paths = [Path(fp) for fp in raw_fps] if raw_fps else None
            return {"study_notes_md": generate_study_notes(Path(inputs["working_directory"]), inputs["transcript_text"], frame_paths)}
            
        elif action == "generate_video_chapters":
            if not self.chapters:
                return {"chapter_text": None}
            from chapter_generator import generate_video_chapters # type: ignore
            return {"chapter_text": generate_video_chapters(Path(inputs["working_directory"]), Path(state.get_output("video_path")).name, inputs["transcript_text"])}
            
        elif action == "score_translation":
            from qa_agent import score_translation # type: ignore
            return score_translation(**inputs)
            
        else:
            raise NotImplementedError(f"Action '{action}' for agent '{agent.id}' not implemented in director.")

    def _print_qa_summary(self) -> None:
        """Run a single QA score per newly-translated video and display a summary table."""
        if not self.session_translated:
            return

        from qa_agent import score_translation  # type: ignore

        console.print()
        table = Table(title="[bold]Translation QA Report[/bold]", show_header=True, header_style="bold cyan",
                      show_lines=False, expand=False)
        table.add_column("Video", style="dim", max_width=42, no_wrap=True)
        table.add_column("Score", justify="center", width=7)
        table.add_column("Critique", no_wrap=False, max_width=60)

        for w_d in self.session_translated:
            stem = w_d.name
            srt_p = w_d / f"{stem}.srt"
            zh_p = w_d / f"{stem}.zh.srt"
            if not srt_p.exists() or not zh_p.exists():
                continue
            try:
                result = score_translation(
                    srt_p.read_text(encoding="utf-8"),
                    zh_p.read_text(encoding="utf-8"),
                )
                score = result.get("qa_score", 0)
                critique = str(result.get("qa_critique", "")).split("\n")[0][:80]  # type: ignore[misc]
                if isinstance(score, (int, float)) and score >= 9:
                    score_str = f"[green]{score}[/green]"
                elif isinstance(score, (int, float)) and score >= 7:
                    score_str = f"[yellow]{score}[/yellow]"
                else:
                    score_str = f"[red]{score}[/red]"
                table.add_row(stem[:42], score_str, critique)  # type: ignore[misc]
            except Exception as e:
                table.add_row(stem[:42], "[red]ERR[/red]", str(e)[:80])  # type: ignore[misc]

        console.print(table)

    def run_all(self, media_files: List[Path]):
        """Runs the entire pipeline on multiple files in parallel."""
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TimeElapsedColumn(), console=console) as progress:
            main_task = progress.add_task("[bold blue]Multi-Agent Orchestration", total=len(media_files))

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(self.process_video, f, progress, main_task): f for f in media_files} # type: ignore

                for fut in as_completed(futures):
                    progress.advance(main_task)

        # Print QA summary once after all videos complete (only newly translated ones)
        self._print_qa_summary()

def main():
    workflow_json = BASE_DIR / "multi_agent_workflow.json"
    if not workflow_json.exists():
        console.print("[bold red]ERROR:[/bold red] multi_agent_workflow.json not found.")
        return

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", type=Path, nargs="*", help="Paths to media files or directories.")
    parser.add_argument("--language", "-l", help="Source language.")
    parser.add_argument("--style", default="academic", help="Translation style.")
    args = parser.parse_args()

    # Discovery
    if args.paths:
        media_files = []
        for p in args.paths:
            if p.is_file() and is_media_file(p): media_files.append(p)
            elif p.is_dir(): media_files.extend([f for f in p.rglob("*") if is_media_file(f)])
    else:
        media_files = [f for f in INPUT_DIR.rglob("*") if is_media_file(f)]
        
    if not media_files:
        console.print("[yellow]No media files found to process.[/yellow]")
        return
        
    engine = WorkflowEngine(workflow_json, language=args.language, style=args.style)
    engine.run_all(media_files)

if __name__ == "__main__":
    main()
