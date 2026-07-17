# Plan: UX-1 — CLI Enhancement + Web Dashboard Upgrade + Input Drag-Drop

## Goal

Make subtitle-forge more **user-friendly** by strengthening three interaction layers:

1. **CLI 強化** — interactive mode, better `--help`, shell completion, desktop notification on completion
2. **Web Dashboard 升級** — modern single-page UI with drag-drop file upload, real-time progress via SSE/WebSocket, task history management
3. **Input Drag-Drop** — drag-and-drop files/folders onto the app to trigger processing (via Flask endpoint + enhanced watchdog)

## Done Criteria

- [x] `main.py` supports `--interactive` mode: guided file selection + parameter config
- [x] `main.py --help` outputs grouped, colourised argument help with examples
- [x] Shell completion script generated (zsh/bash) via `--completion`
- [x] Desktop notification sent on pipeline completion (via `osascript` on macOS, fallback `terminal-notifier`)
- [x] `server.py` upgraded with drop-zone upload, real-time progress (HTMX polling), task history table
- [x] New `POST /upload` Flask endpoint accepts file POST → triggers pipeline in background thread
- [x] All existing functionality (`main.py` without new flags) remains unchanged
- [x] Tests pass: `pytest tests/ -x`

## Tasks

| # | Task | Est. | Deps | Owner |
|---|------|------|------|-------|
| 0 | Setup + characterization tests | 30m | — | ✅ Done |
| 1 | CLI: `--interactive` mode (file picker + config prompt) | 45m | 0 | ✅ Done |
| 2 | CLI: `--completion` (shell completion script generation) | 30m | 0 | ✅ Done |
| 3 | CLI: Desktop notification on completion (`osascript`/`terminal-notifier`) | 20m | 0 | ✅ Done |
| 4 | Web: Upgrade server.py — drop-zone upload + HTMX progress + task history | 2h | 0 | ✅ Done |
| 5 | Web: POST `/upload` endpoint → triggers pipeline in thread | (absorbed into 4) | 4 | ✅ Done |
| 6 | Integration: verify all paths work end-to-end | 30m | 1,2,3,4,5 | ✅ Done |

### Task 0: Setup + characterization tests

- Read full `main.py`, `server.py`, check existing tests
- Write smoke tests for `main.py` argument parsing and `server.py` routes
- Verify `Flask` + `rich` already in requirements.txt (yes: Flask==3.1.3, rich==14.3.3)

### Task 1: CLI `--interactive` mode

Add `--interactive` / `-i` flag to `main.py`:

```
$ ./venv/bin/python3 main.py --interactive

  Subtitle Forge — Interactive Mode

  📁 Input files (drag paths or type comma-separated):
  > path/to/video.mp4, path/to/video2.mkv

  🌐 Language (enter=auto):
  > zh

  🎨 Style [academic/casual/exam-focused] (enter=academic):
  >

  Generating chapters? [Y/n]:
  > Y

  ⏳ Processing 2 files... (Ctrl+C to cancel)
```

Implementation:
- Use `rich.prompt.Prompt` / `rich.prompt.Confirm` for interactive prompts
- Reuse existing `main()` logic — just wrap the argument parsing
- Default to current directory `input/` if no paths provided
- Show summary before execution

### Task 2: CLI `--completion` (shell completion)

- Add `parser.add_argument("--completion", choices=["zsh", "bash"])`
- Generate script inline or from a template
- Print to stdout so user can eval/source
- For zsh: `_subtitle_forge` completion function
- For bash: `_subtitle_forge_completion` function

### Task 3: Desktop notification

- On completion in `main()` and `print_summary()`, call:
  ```python
  import subprocess
  try:
      subprocess.run(["terminal-notifier",
          "-title", "Subtitle Forge",
          "-message", f"Done! {len(media_files)} file(s) processed.",
          "-sound", "default"], timeout=3)
  except: pass
  ```
- Check `terminal-notifier` is installed, warn if not
- Add `--no-notify` flag to suppress

### Task 4: Web Dashboard upgrade (`server.py`)

Rewrite `server.py` with:

- **Drop-zone upload**: HTML5 drag-and-drop zone, POST `/upload` with file
- **SSE progress stream**: `GET /stream` endpoint using Server-Sent Events
- **Task history table**: read from `usage_log.jsonl` + `state.json` per task
- **Hover/click preview**: show subtitle content, completion status
- **Minimal CSS**: single-file HTML (keep Flask template_string pattern for simplicity)
- Use HTMX from CDN for interactivity (no build step)

Layout:
```
┌─────────────────────────────────────────────┐
│  Subtitle Forge Dashboard           v1.1    │
├─────────────────────────────────────────────┤
│  ┌───────────────────────────────────────┐  │
│  │       📁 Drop files here              │  │
│  │       or click to browse              │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  ┌──── Active Tasks ──────────────────────┐ │
│  │  video1.mp4   ████████░░ 80%  ASR     │ │
│  │  video2.mkv   ██████████ 100% Done    │ │
│  └───────────────────────────────────────┘  │
│                                             │
│  ┌──── History ───────────────────────────┐ │
│  │  Time        │ File        │ Cost     │ │
│  │  14:32:01    │ video1.srt  │ $0.00    │ │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### Task 5: POST `/upload` endpoint

- Accept multipart file upload
- Save to `input/`
- Trigger pipeline in background thread
- Return task ID immediately
- Worker thread updates progress state (shared dict or temp file)
- SSE stream reads progress state

### Task 6: Integration verification

- Run `main.py -h` → check grouped help with examples
- Run `main.py --interactive` with Ctrl+C test
- Run `main.py --completion zsh` → valid shell function
- Start server, upload file via curl, check progress stream
- Run `main.py` on a real file → desktop notification fires
- `pytest tests/ -x` passes

## Files Changed

| File | Change |
|------|--------|
| `main.py` | Add `--interactive`, `--completion`, `--no-notify` flags |
| `server.py` | Complete rewrite with drop-zone, SSE, upload endpoint |
| `requirements.txt` | Add `terminal-notifier` (optional, macOS only) |

## Rollback

```bash
git checkout -- main.py server.py requirements.txt
```

## Commit Message

```
feat(ux): CLI interactive mode, web dashboard upgrade, drag-drop upload (UX-1)

- Add --interactive mode with guided file selection and config prompts
- Add --completion zsh/bash for shell autocomplete
- Add desktop notification on pipeline completion (terminal-notifier)
- Upgrade web dashboard with drop-zone upload, SSE progress stream, task history
- Add POST /upload endpoint to trigger pipeline from web UI
- All existing CLI flags remain unchanged
```
