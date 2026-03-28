from flask import Flask, render_template_string, send_from_directory  # type: ignore
import os
import json
from pathlib import Path

app = Flask(__name__)
BASE_DIR = Path(__file__).parent.absolute()
OUTPUT_DIR = BASE_DIR / "output"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Subtitle Forge Dashboard</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { background: #f8f9fa; padding: 20px; font-family: 'Inter', sans-serif; }
        .card { border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .status-badge { border-radius: 20px; padding: 4px 12px; font-size: 0.8rem; }
    </style>
</head>
<body>
    <div class="container">
        <h2 class="mb-4">Subtitle Forge Dashboard</h2>
        
        <div class="row">
            <div class="col-md-8">
                <div class="card p-3">
                    <h4>Recent Activities</h4>
                    <table class="table table-hover">
                        <thead><tr><th>Time</th><th>Category</th><th>Detail</th><th>Cost</th></tr></thead>
                        <tbody>
                            {% for row in logs %}
                            <tr>
                                <td class="dim">{{ row.timestamp }}</td>
                                <td><span class="badge bg-secondary">{{ row.category }}</span></td>
                                <td>{{ row.detail }}</td>
                                <td class="text-success">${{ "%.4f"|format(row.cost) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="col-md-4">
                <div class="card p-3">
                    <h4>Processed Videos</h4>
                    <ul class="list-group list-group-flush">
                        {% for folder in folders %}
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            {{ folder }}
                            <span class="status-badge bg-info text-dark">Ready</span>
                        </li>
                        {% endfor %}
                    </ul>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    # Read JSONL logs
    logs = []
    log_path = BASE_DIR / "usage_log.jsonl"
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip(): logs.append(json.loads(line))
    logs.reverse() # newest first
    
    # List output folders
    folders = []
    if OUTPUT_DIR.exists():
        folders = [d.name for d in OUTPUT_DIR.iterdir() if d.is_dir()]
    
    return render_template_string(HTML_TEMPLATE, logs=logs[:20], folders=folders)  # type: ignore

if __name__ == "__main__":
    app.run(port=5000)
