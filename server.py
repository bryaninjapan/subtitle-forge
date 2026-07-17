"""
server.py — Subtitle Forge Web Dashboard.

Upgraded with:
  - Drop-zone file upload (HTML5 drag-and-drop)
  - Real-time progress bar (HTMX polling)
  - Task history table from usage_log.jsonl
  - Output directory browser
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template_string, request, url_for  # type: ignore
from flask_cors import CORS  # type: ignore
from werkzeug.utils import secure_filename  # type: ignore

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()
# Enable CORS for Tauri dev server
CORS(app, origins=["http://localhost:1420", "tauri://localhost", "https://tauri.localhost"])
# Limit upload size to 4 GB (single file)
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024 * 1024

BASE_DIR = Path(__file__).parent.absolute()
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
MULTI_AGENT_WORKFLOW = BASE_DIR / "multi_agent_workflow.json"

# Allowed file extensions (same as asr_engine)
ALLOWED_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".m4v", ".webm",
                      ".mp3", ".wav", ".m4a", ".aac"}

# ── In-memory progress store ─────────────────────────────────────────────
progress_store: dict[str, dict] = {}
_progress_lock = threading.Lock()


def set_progress(task_id: str, **kwargs) -> None:
    with _progress_lock:
        if task_id not in progress_store:
            progress_store[task_id] = {"file": "", "pct": 0, "stage": "queued", "message": "", "error": ""}
        progress_store[task_id].update(kwargs)
        progress_store[task_id]["ts"] = time.time()


def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


# ── Background processing ────────────────────────────────────────────────

def _process_file(task_id: str, filepath: Path) -> None:
    """Run the full Subtitle Forge pipeline on a single file in a background thread."""
    set_progress(task_id, pct=5, stage="extracting", message="Extracting audio...")
    try:
        from director import WorkflowEngine

        set_progress(task_id, pct=15, stage="initializing", message="Initializing engine...")
        engine = WorkflowEngine(
            MULTI_AGENT_WORKFLOW,
            language=None,  # auto-detect
            style="academic",
            chapters=True,
        )

        set_progress(task_id, pct=30, stage="processing", message="Pipeline running...")

        # Run in a separate thread but we track progress by file count
        # The engine processes each file through ASR→Translate→Notes→Chapters
        engine.run_all([filepath])

        set_progress(task_id, pct=100, stage="done", message="Complete!")
    except Exception as e:
        set_progress(task_id, pct=0, stage="error", message=str(e), error=str(e))


# ── Routes ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/progress")
def get_progress():
    """Return all tasks with their current progress (for HTMX polling)."""
    with _progress_lock:
        tasks = dict(progress_store)
    return jsonify(tasks)


@app.route("/history")
def get_history():
    """Return task history from usage_log.jsonl."""
    records = []
    log_path = BASE_DIR / "usage_log.jsonl"
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    records.reverse()  # newest first
    return jsonify(records[:50])


@app.route("/outputs")
def get_outputs():
    """Return list of processed output folders."""
    folders = []
    if OUTPUT_DIR.exists():
        for d in sorted(OUTPUT_DIR.iterdir()):
            if d.is_dir():
                files = [f.name for f in d.iterdir() if f.suffix in {".srt", ".zh.srt", ".bilingual.srt", ".vtt", ".txt", ".md"}]
                folders.append({"name": d.name, "files": sorted(files)})
    return jsonify(folders)


@app.route("/outputs/<path:filepath>")
def get_output_file(filepath: str):
    """Serve a file from the output directory."""
    file_path = (OUTPUT_DIR / filepath).resolve()
    # Security: ensure the resolved path is within OUTPUT_DIR
    if not str(file_path).startswith(str(OUTPUT_DIR.resolve())):
        return jsonify({"error": "Access denied"}), 403
    if not file_path.exists() or not file_path.is_file():
        return jsonify({"error": "File not found"}), 404
    from flask import send_file  # type: ignore
    return send_file(str(file_path))


@app.route("/settings", methods=["GET", "POST"])
def handle_settings():
    """GET: read settings.yaml.  POST: write settings.yaml."""
    settings_path = BASE_DIR / "settings.yaml"
    import yaml  # type: ignore

    if request.method == "GET":
        if not settings_path.exists():
            return jsonify({})
        with open(settings_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return jsonify(data)

    # POST: merge provided keys into settings.yaml
    updates = request.get_json(force=True, silent=True) or {}
    current = {}
    if settings_path.exists():
        with open(settings_path, "r", encoding="utf-8") as f:
            current = yaml.safe_load(f) or {}

    # Deep merge
    def deep_merge(base: dict, overrides: dict) -> dict:
        result = dict(base)
        for k, v in overrides.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    merged = deep_merge(current, updates)
    with open(settings_path, "w", encoding="utf-8") as f:
        yaml.dump(merged, f, allow_unicode=True, default_flow_style=False)
    return jsonify({"status": "ok"})


@app.route("/cancel/<task_id>", methods=["POST"])
def cancel_task(task_id: str):
    """Mark a running task as cancelled."""
    with _progress_lock:
        if task_id in progress_store:
            progress_store[task_id]["stage"] = "cancelled"
            progress_store[task_id]["message"] = "Cancelled by user"
            return jsonify({"status": "cancelled", "task_id": task_id})
    return jsonify({"error": "Task not found", "task_id": task_id}), 404


@app.route("/upload", methods=["POST"])
def upload_file():
    """Accept uploaded file, save to input/, start background pipeline."""
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "" or not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}"}), 400

    # Save file
    safe_name = secure_filename(file.filename)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = INPUT_DIR / safe_name
    file.save(str(dest))

    # Spawn background processing
    task_id = str(uuid.uuid4())[:8]
    set_progress(task_id, file=safe_name, pct=0, stage="queued", message="Queued...")

    t = threading.Thread(target=_process_file, args=(task_id, dest), daemon=True)
    t.start()

    if request.accept_mimetypes.accept_json:
        return jsonify({"task_id": task_id, "file": safe_name, "status": "queued"})
    return redirect(url_for("index"))


# ── HTML Template ────────────────────────────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Subtitle Forge Dashboard</title>
  <script src="https://unpkg.com/htmx.org@2.0.4"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
           background: #0f172a; color: #e2e8f0; min-height: 100vh; }
    .container { max-width: 960px; margin: 0 auto; padding: 24px 16px; }
    h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 24px; color: #f8fafc; display: flex; align-items: center; gap: 10px; }
    h1 small { font-size: 0.7rem; font-weight: 400; color: #64748b; margin-left: auto; }

    /* Drop Zone */
    .drop-zone { border: 2px dashed #334155; border-radius: 12px; padding: 40px 20px;
                 text-align: center; cursor: pointer; transition: all .2s;
                 background: #1e293b; margin-bottom: 24px; position: relative; }
    .drop-zone:hover, .drop-zone.drag-over { border-color: #3b82f6; background: #1e3a5f; }
    .drop-zone .icon { font-size: 2rem; margin-bottom: 8px; }
    .drop-zone p { color: #94a3b8; font-size: 0.9rem; }
    .drop-zone input[type=file] { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
    .drop-zone .hint { margin-top: 8px; font-size: 0.75rem; color: #475569; }

    /* Cards */
    .card { background: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
    .card h2 { font-size: 1rem; font-weight: 600; margin-bottom: 12px; color: #94a3b8; }

    /* Progress bars */
    .task-row { display: flex; align-items: center; gap: 12px; padding: 8px 0;
                border-bottom: 1px solid #0f172a; }
    .task-row:last-child { border-bottom: none; }
    .task-file { flex: 0 0 30%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.85rem; }
    .task-bar-wrap { flex: 1; height: 8px; background: #0f172a; border-radius: 4px; overflow: hidden; }
    .task-bar { height: 100%; border-radius: 4px; transition: width .5s ease; }
    .task-bar.queued { background: #475569; width: 10%; }
    .task-bar.running { background: #3b82f6; }
    .task-bar.done { background: #22c55e; }
    .task-bar.error { background: #ef4444; width: 100%; }
    .task-stage { flex: 0 0 80px; font-size: 0.75rem; color: #64748b; text-align: right; }
    .task-pct { flex: 0 0 40px; font-size: 0.8rem; font-weight: 600; text-align: right; }
    .empty-msg { color: #475569; font-size: 0.85rem; padding: 16px 0; text-align: center; }

    /* History table */
    table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    th { text-align: left; padding: 8px 6px; color: #64748b; font-weight: 500;
         border-bottom: 1px solid #334155; }
    td { padding: 6px; border-bottom: 1px solid #1e293b; }
    tr:hover td { background: #0f172a40; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; }
    .badge-asr { background: #1e3a5f; color: #60a5fa; }
    .badge-translate { background: #14532d; color: #4ade80; }
    .badge-notes { background: #3b0764; color: #c084fc; }
    .badge-chapter { background: #451a03; color: #fb923c; }
    .badge-error { background: #450a0a; color: #f87171; }
    .cost { color: #4ade80; font-family: 'SF Mono', monospace; }

    /* Output browser */
    .output-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px; }
    .output-item { background: #0f172a; border-radius: 8px; padding: 12px; font-size: 0.8rem; }
    .output-item .name { font-weight: 600; color: #e2e8f0; margin-bottom: 4px; }
    .output-item .file { color: #64748b; font-size: 0.75rem; }

    @media (max-width: 640px) {
      .task-file { flex-basis: 40%; }
      .task-stage { flex-basis: 60px; }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>
      <span>🎬 Subtitle Forge</span>
      <small>v1.1</small>
    </h1>

    <!-- Drop Zone -->
    <div class="drop-zone" id="dropzone">
      <div class="icon">📁</div>
      <p>Drop media files here or click to browse</p>
      <p class="hint">Supports: mp4, mkv, mov, avi, webm, mp3, wav, m4a, aac</p>
      <form action="/upload" method="post" enctype="multipart/form-data"
            hx-encoding="multipart/form-data" hx-post="/upload" hx-target="#tasks"
            hx-swap="innerHTML" hx-trigger="change">
        <input type="file" name="file" multiple>
      </form>
    </div>

    <!-- Active Tasks -->
    <div class="card">
      <h2>⚙️ Active Tasks</h2>
      <div id="tasks"
           hx-get="/progress-html"
           hx-trigger="every 2s"
           hx-swap="innerHTML">
        <div class="empty-msg">No active tasks</div>
      </div>
    </div>

    <!-- History -->
    <div class="card">
      <h2>📋 History</h2>
      <div id="history"
           hx-get="/history-html"
           hx-trigger="load, every 10s"
           hx-swap="innerHTML">
        <div class="empty-msg">Loading...</div>
      </div>
    </div>

    <!-- Output Browser -->
    <div class="card">
      <h2>📂 Outputs</h2>
      <div id="outputs"
           hx-get="/outputs-html"
           hx-trigger="load, every 30s"
           hx-swap="innerHTML">
        <div class="empty-msg">Loading...</div>
      </div>
    </div>
  </div>

  <script>
    // Drag-and-drop visual feedback
    document.addEventListener('htmx:afterRequest', function(evt) {
      if (evt.detail.pathInfo.requestPath === '/upload') {
        document.querySelector('.drop-zone input[type=file]').value = '';
      }
    });
  </script>
</body>
</html>
"""


# ── HTMX partial endpoints ──────────────────────────────────────────────

@app.route("/progress-html")
def progress_html():
    """Return HTML snippet for active tasks (for HTMX polling)."""
    with _progress_lock:
        tasks = dict(progress_store)

    # Only show non-expired tasks (last 5 min), and tasks that are recent
    now = time.time()
    active = {k: v for k, v in tasks.items()
              if v.get("stage") != "done" or (now - v.get("ts", 0)) < 300}

    if not active:
        return '<div class="empty-msg">No active tasks</div>'

    parts = []
    for tid, t in sorted(active.items(), key=lambda x: x[1].get("ts", 0), reverse=True):
        pct = t.get("pct", 0)
        stage = t.get("stage", "queued")
        msg = t.get("message", "")
        fname = t.get("file", tid)
        bar_class = "running" if stage in ("extracting", "initializing", "processing") else stage
        parts.append(f"""<div class="task-row">
  <span class="task-file" title="{fname}">{fname}</span>
  <div class="task-bar-wrap">
    <div class="task-bar {bar_class}" style="width:{pct}%"></div>
  </div>
  <span class="task-stage">{msg}</span>
  <span class="task-pct">{pct:.0f}%</span>
</div>""")
    return "".join(parts)


@app.route("/history-html")
def history_html():
    """Return HTML snippet for history table."""
    records = []
    log_path = BASE_DIR / "usage_log.jsonl"
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    records.reverse()
    records = records[:30]

    if not records:
        return '<div class="empty-msg">No history yet</div>'

    rows = []
    for r in records:
        cat = r.get("category", "")
        badge_class = "badge-asr" if "asr" in cat.lower() else \
                      "badge-translate" if "translate" in cat.lower() else \
                      "badge-notes" if "note" in cat.lower() else \
                      "badge-chapter" if "chapter" in cat.lower() else \
                      "badge-error" if "error" in cat.lower() or "fail" in cat.lower() else ""
        cost = r.get("cost", 0)
        ts = r.get("timestamp", "")[:19]  # trim fractional seconds
        detail = r.get("detail", "")[:60]
        rows.append(f"""<tr>
  <td>{ts}</td>
  <td><span class="badge {badge_class}">{cat}</span></td>
  <td>{detail}</td>
  <td class="cost">${float(cost):.4f}</td>
</tr>""")
    return f"""<table><thead><tr>
  <th>Time</th><th>Category</th><th>Detail</th><th>Cost</th>
</tr></thead><tbody>{"".join(rows)}</tbody></table>"""


@app.route("/outputs-html")
def outputs_html():
    """Return HTML snippet for output browser."""
    folders = []
    if OUTPUT_DIR.exists():
        for d in sorted(OUTPUT_DIR.iterdir()):
            if d.is_dir():
                files = sorted(f.name for f in d.iterdir()
                               if f.suffix in {".srt", ".zh.srt", ".bilingual.srt", ".vtt", ".txt", ".md",
                                                ".apkg"})
                folders.append((d.name, files))

    if not folders:
        return '<div class="empty-msg">No processed outputs yet</div>'

    parts = []
    for name, files in folders[:20]:
        file_list = "<br>".join(f"<span class='file'>{f}</span>" for f in files[:6])
        if len(files) > 6:
            file_list += f"<br><span class='file' style='color:#475569'>+{len(files)-6} more</span>"
        parts.append(f"""<div class="output-item">
  <div class="name">{name}</div>
  {file_list}
</div>""")
    return f"""<div class="output-grid">{"".join(parts)}</div>"""


# ── Main ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(port=5000, debug=True)
