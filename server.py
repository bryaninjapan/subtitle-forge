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
import socket
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
    """Run the Subtitle Forge pipeline on a single file in a background thread."""
    set_progress(task_id, pct=5, stage="extracting", message="Extracting audio...")
    try:
        from director import WorkflowEngine

        set_progress(task_id, pct=15, stage="initializing", message="Initializing engine...")

        # Read toggle params from progress store
        with _progress_lock:
            task_info = progress_store.get(task_id, {})

        engine = WorkflowEngine(
            MULTI_AGENT_WORKFLOW,
            language=None,
            style="academic",
            chapters=task_info.get("chapters", True),
            translate=task_info.get("translate", True),
            notes=task_info.get("notes", True),
            prompt=task_info.get("prompt", ""),
        )

        set_progress(task_id, pct=30, stage="processing", message="Pipeline running...")
        engine.run_all([filepath])

        set_progress(task_id, pct=100, stage="done", message="Complete!")
    except Exception as e:
        set_progress(task_id, pct=0, stage="error", message=str(e), error=str(e))


# ── Model Management ────────────────────────────────────────────────────

ASR_MODELS = [
    {"id": "Qwen3-ASR-0.6B", "repo": "Qwen/Qwen3-ASR-0.6B", "size_mb": 1200},
    {"id": "Qwen3-ForcedAligner-0.6B", "repo": "Qwen/Qwen3-ForcedAligner-0.6B", "size_mb": 1800},
]


def _get_model_cache_dir(repo_id: str) -> Path:
    """Get the HuggingFace cache directory for a model repo."""
    name = repo_id.replace("/", "--")
    return Path.home() / ".cache" / "huggingface" / "hub" / f"models--{name}"


def _check_model_status(repo_id: str) -> dict:
    """Check if a HuggingFace model is downloaded and return status."""
    cache_dir = _get_model_cache_dir(repo_id)
    snapshots_dir = cache_dir / "snapshots"
    refs_dir = cache_dir / "refs"

    if not snapshots_dir.exists():
        return {"status": "not_downloaded", "size_mb": 0}

    # Check for downloaded snapshots
    snapshots = list(snapshots_dir.iterdir()) if snapshots_dir.exists() else []
    # Read main branch ref to find current snapshot
    main_ref = ""
    if refs_dir.exists():
        main_file = refs_dir / "main"
        if main_file.exists():
            main_ref = main_file.read_text().strip()

    if not snapshots:
        return {"status": "not_downloaded", "size_mb": 0}

    # Calculate total size
    total_bytes = 0
    for snap in snapshots:
        for f in snap.rglob("*"):
            if f.is_file():
                total_bytes += f.stat().st_size

    target_snap = None
    if main_ref:
        target_snap = snapshots_dir / main_ref
        if target_snap.exists():
            return {"status": "downloaded", "size_mb": round(total_bytes / 1024 / 1024)}
        else:
            return {"status": "downloading", "size_mb": round(total_bytes / 1024 / 1024)}

    return {"status": "downloaded", "size_mb": round(total_bytes / 1024 / 1024)}


@app.route("/models/status")
def get_model_status():
    """Return status of all known ASR models."""
    results = []
    for m in ASR_MODELS:
        info = _check_model_status(m["repo"])
        results.append({
            "id": m["id"],
            "repo": m["repo"],
            "status": info["status"],
            "size_mb": info["size_mb"],
        })
    return jsonify({"models": results})


@app.route("/models/download/<model_id>")
def download_model(model_id: str):
    """Trigger download of a specific model in the background."""
    model = next((m for m in ASR_MODELS if m["id"] == model_id), None)
    if not model:
        return jsonify({"error": f"Unknown model: {model_id}"}), 404

    # Check if already downloaded
    info = _check_model_status(model["repo"])
    if info["status"] == "downloaded":
        return jsonify({"status": "already_downloaded", "model": model_id})

    # Start background download
    task_id = f"download_{model_id}"
    from config import ASR_MAX_CONCURRENT
    set_progress(task_id, pct=0, stage="downloading", message=f"Downloading {model_id}...")

    def _download_worker(task_id: str, repo_id: str):
        try:
            from huggingface_hub import snapshot_download  # type: ignore
            set_progress(task_id, pct=10, stage="downloading", message=f"Downloading {repo_id}...")

            def _on_progress(completed: int, total: int):
                pct = int((completed / max(total, 1)) * 100)
                set_progress(task_id, pct=pct, stage="downloading", message=f"Downloading {repo_id}...")

            snapshot_download(
                repo_id=repo_id,
                resume_download=True,
                ignore_patterns=["*.h5", "*.ot", "*.msgpack"],
            )
            set_progress(task_id, pct=100, stage="done", message=f"Downloaded {repo_id}")
        except Exception as e:
            set_progress(task_id, pct=0, stage="error", message=str(e), error=str(e))

    t = threading.Thread(target=_download_worker, args=(task_id, model["repo"]), daemon=True)
    t.start()

    return jsonify({"status": "downloading", "model": model_id, "task_id": task_id})


# ── Endpoint Service ────────────────────────────────────────────────────

ENDPOINT_PORT = 11435
_endpoint_access_key: str = ""
_endpoint_server_thread: threading.Thread | None = None
_endpoint_server_running = False


def _generate_access_key() -> str:
    """Generate a random access key."""
    import secrets
    return secrets.token_urlsafe(16)


def _run_endpoint_server():
    """Run a lightweight upload server on a separate port."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json as json_module
    import cgi
    from urllib.parse import urlparse

    class EndpointHandler(BaseHTTPRequestHandler):
        def _send_json(self, code: int, data: dict):
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json_module.dumps(data).encode())

        def _check_auth(self) -> bool:
            auth = self.headers.get("Authorization", "")
            expected = f"Bearer {_endpoint_access_key}"
            if auth != expected:
                self._send_json(403, {"error": "Invalid or missing access key"})
                return False
            return True

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.end_headers()

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/":
                self._send_json(200, {
                    "status": "running",
                    "name": "Subtitle Forge Endpoint",
                })
            elif path == "/health":
                self._send_json(200, {"status": "ok"})
            else:
                self._send_json(404, {"error": "Not found"})

        def do_POST(self):
            path = urlparse(self.path).path
            if path == "/upload":
                if not self._check_auth():
                    return
                # Parse multipart form
                content_type = self.headers.get("Content-Type", "")
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={
                        "REQUEST_METHOD": "POST",
                        "CONTENT_TYPE": content_type,
                    }
                )
                if "file" not in form:
                    self._send_json(400, {"error": "No file part"})
                    return

                file_item = form["file"]
                if not file_item.filename:
                    self._send_json(400, {"error": "No file selected"})
                    return

                # Save file to input directory
                from werkzeug.utils import secure_filename
                safe_name = secure_filename(file_item.filename or "upload")
                dest = INPUT_DIR / safe_name
                with open(dest, "wb") as f:
                    f.write(file_item.file.read())

                # Start processing
                task_id = str(uuid.uuid4())[:8]
                set_progress(task_id, file=safe_name, pct=0, stage="queued", message="Queued...")
                t = threading.Thread(target=_process_file, args=(task_id, dest), daemon=True)
                t.start()

                self._send_json(200, {
                    "task_id": task_id,
                    "file": safe_name,
                    "status": "queued",
                })
            else:
                self._send_json(404, {"error": "Not found"})

        def log_message(self, format, *args):
            pass  # Suppress HTTP server logs

    global _endpoint_server_running
    _endpoint_server_running = True
    server = HTTPServer(("0.0.0.0", ENDPOINT_PORT), EndpointHandler)
    try:
        server.serve_forever()
    except OSError:
        pass
    finally:
        _endpoint_server_running = False
        server.server_close()


@app.route("/endpoint/start", methods=["POST"])
def start_endpoint():
    """Start the endpoint upload server."""
    global _endpoint_server_thread, _endpoint_access_key
    if _endpoint_server_thread and _endpoint_server_thread.is_alive():
        return jsonify({"status": "already_running", "port": ENDPOINT_PORT, "key": _endpoint_access_key})

    _endpoint_access_key = _generate_access_key()
    _endpoint_server_thread = threading.Thread(target=_run_endpoint_server, daemon=True)
    _endpoint_server_thread.start()

    # Wait briefly for server to start
    import time
    time.sleep(0.5)

    return jsonify({
        "status": "started",
        "port": ENDPOINT_PORT,
        "url": f"http://{_get_local_ip()}:{ENDPOINT_PORT}",
        "key": _endpoint_access_key,
    })


@app.route("/endpoint/stop", methods=["POST"])
def stop_endpoint():
    """Stop the endpoint upload server."""
    global _endpoint_server_thread, _endpoint_server_running
    if not _endpoint_server_thread or not _endpoint_server_thread.is_alive():
        return jsonify({"status": "not_running"})

    _endpoint_server_running = False
    # Send a dummy request to unblock server
    import urllib.request
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{ENDPOINT_PORT}/health", timeout=1)
    except Exception:
        pass

    _endpoint_server_thread = None
    return jsonify({"status": "stopped"})


@app.route("/endpoint/status")
def get_endpoint_status():
    """Return endpoint server status."""
    running = _endpoint_server_thread is not None and _endpoint_server_thread.is_alive()
    return jsonify({
        "running": running,
        "port": ENDPOINT_PORT if running else None,
        "url": f"http://{_get_local_ip()}:{ENDPOINT_PORT}" if running else None,
        "key": _endpoint_access_key if running else None,
    })


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


@app.route("/audio/<path:filepath>")
def serve_audio(filepath: str):
    """Serve audio/video files for playback with Range header support."""
    # Search input dir first, then output dir
    input_path = (INPUT_DIR / filepath).resolve()
    output_path = (OUTPUT_DIR / filepath).resolve()

    if input_path.exists() and str(input_path).startswith(str(INPUT_DIR.resolve())):
        file_path = input_path
    elif output_path.exists() and str(output_path).startswith(str(OUTPUT_DIR.resolve())):
        file_path = output_path
    else:
        return jsonify({"error": "File not found"}), 404

    from flask import send_file  # type: ignore
    return send_file(str(file_path), conditional=True)


def _compute_waveform_peaks(audio_path: Path) -> list[float]:
    """Extract adaptive-resolution waveform peaks from audio.

    Uses ffmpeg to decode to mono 16-bit PCM, then downsamples
    to an adaptive number of points based on duration.
    """
    import struct
    import subprocess

    duration = 0.0
    try:
        dur_cmd = ["ffprobe", "-v", "error", "-show_entries",
                     "format=duration", "-of",
                     "csv=p=0", str(audio_path)]
        dur_out = subprocess.run(dur_cmd, capture_output=True, text=True, timeout=30)
        duration = float(dur_out.stdout.strip() or 0)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        duration = 0.0

    # Adaptive peak count
    if duration <= 0:
        num_peaks = 1000
    elif duration < 60:          # < 1 min → ~50 pts/s
        num_peaks = max(200, int(duration * 50))
    elif duration < 600:         # < 10 min → ~10 pts/s
        num_peaks = int(duration * 10)
    else:                        # > 10 min → cap at 10000
        num_peaks = min(int(duration * 10), 10000)

    try:
        # Decode to mono 16-bit PCM
        cmd = [
            "ffmpeg", "-v", "quiet", "-i", str(audio_path),
            "-ac", "1", "-ar", "8000",  # 8kHz mono is sufficient for waveform
            "-f", "s16le", "-",
        ]
        raw = subprocess.run(cmd, capture_output=True, timeout=300).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []

    if not raw:
        return []

    # Decode raw PCM samples
    samples = struct.unpack(f"<{len(raw) // 2}h", raw)

    # Compute peaks (max amplitude over windowed samples)
    window = max(1, len(samples) // num_peaks)
    peaks: list[float] = []
    for i in range(0, len(samples) - window + 1, window):
        chunk = samples[i:i + window]
        peak = max(abs(s) for s in chunk) / 32768.0  # normalize to 0.0-1.0
        peaks.append(peak)

    return peaks


@app.route("/waveform/<task_id>")
def get_waveform(task_id: str):
    """Return waveform peaks for a completed task's audio."""
    with _progress_lock:
        task = progress_store.get(task_id)

    audio_file: Path | None = None
    if task and "file" in task:
        fname = task["file"]
        for base in [INPUT_DIR, OUTPUT_DIR]:
            for p in base.iterdir():
                if p.is_file() and p.name == fname:
                    audio_file = p
                    break
            if audio_file:
                break

    if not audio_file or not audio_file.exists():
        return jsonify({"error": "Audio file not found for this task"}), 404

    peaks = _compute_waveform_peaks(audio_file)
    return jsonify({
        "peaks": peaks,
        "num_peaks": len(peaks),
    })


@app.route("/timestamps/<task_id>")
def get_word_timestamps(task_id: str):
    """Return word-level timestamps for a completed task."""
    with _progress_lock:
        task = progress_store.get(task_id)

    if not task or "file" not in task:
        return jsonify({"error": "Task not found"}), 404

    fname = task["file"]
    stem = Path(fname).stem
    for subdir in OUTPUT_DIR.iterdir():
        if subdir.is_dir():
            words_path = subdir / f"{stem}.words.json"
            if words_path.exists():
                try:
                    return jsonify(json.loads(words_path.read_text(encoding="utf-8")))
                except Exception:
                    return jsonify({"error": "Failed to parse words file"}), 500

    return jsonify({"error": "Word timestamps not found"}), 404


def _get_local_ip() -> str:
    """Get the local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        # Doesn't need to reach, just to determine the interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


@app.route("/endpoint/qrcode")
def get_endpoint_qrcode():
    """Return a QR code PNG for the server upload URL."""
    import io
    import qrcode  # type: ignore

    ip = _get_local_ip()
    port = request.host.split(":")[1] if ":" in request.host else "5000"
    url = f"http://{ip}:{port}"

    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#111827", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    from flask import Response  # type: ignore
    return Response(buf.getvalue(), mimetype="image/png")


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


@app.route("/pipeline", methods=["POST"])
def run_pipeline():
    """Accept file + toggle params, run selective pipeline.

    Multipart form with optional JSON fields:
      - file: binary media file (required)
      - translate: "true"/"false" (default: false)
      - notes: "true"/"false" (default: false)
      - chapters: "true"/"false" (default: false)
      - prompt: optional hint text for recognition
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "" or not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed"}), 400

    # Save file
    safe_name = secure_filename(file.filename)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = INPUT_DIR / safe_name
    file.save(str(dest))

    # Read toggle params from form
    translate = request.form.get("translate", "false").lower() == "true"
    notes = request.form.get("notes", "false").lower() == "true"
    chapters = request.form.get("chapters", "false").lower() == "true"
    prompt = request.form.get("prompt", "")

    # Spawn background processing
    task_id = str(uuid.uuid4())[:8]
    set_progress(
        task_id,
        file=safe_name,
        pct=0,
        stage="queued",
        message="Queued...",
        translate=translate,
        notes=notes,
        chapters=chapters,
        prompt=prompt,
    )

    t = threading.Thread(target=_process_file, args=(task_id, dest), daemon=True)
    t.start()

    return jsonify({
        "task_id": task_id,
        "file": safe_name,
        "status": "queued",
        "translate": translate,
        "notes": notes,
        "chapters": chapters,
    })


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
