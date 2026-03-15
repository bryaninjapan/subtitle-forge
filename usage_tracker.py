import json
import time
import threading
from pathlib import Path
from config import BASE_DIR

USAGE_LOG_PATH = BASE_DIR / "usage_log.json"
USAGE_MD_PATH = BASE_DIR / "pipeline_report.md"
FAILURE_MD_PATH = BASE_DIR / "pipeline_failures.md"

_log_lock = threading.Lock()

# Wave 7: Adaptive Concurrency Scaling State
# When any thread hits a 429, it sets this 'backoff_signal'
# All other threads check this before starting new API calls
_backoff_until = 0.0
_backoff_lock = threading.Lock()

def signal_backoff(seconds: float = 30.0):
    """Signal all threads to back off for a period."""
    global _backoff_until
    with _backoff_lock:
        new_target = time.time() + seconds
        if new_target > _backoff_until:
            _backoff_until = new_target
            print(f"\n⚠️  [Adaptive Scaling] Rate limit detected. Throttling all workers for {seconds:.0f}s...")

def check_backoff():
    """Check if we are in a backoff period. If so, block until it's over."""
    global _backoff_until
    while True:
        wait_time = _backoff_until - time.time()
        if wait_time <= 0:
            break
        time.sleep(min(wait_time, 2.0))

def log_usage(category: str, detail: str, input_tokens: int, output_tokens: int):
    """Log token usage to JSON and a Markdown report."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    total_tokens = input_tokens + output_tokens
    cost = (input_tokens * 0.000000075) + (output_tokens * 0.0000003)
    
    usage = {
        "timestamp": timestamp,
        "category": category, # e.g., "ASR", "Translation", "Notes"
        "detail": detail,    # e.g., filename
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": cost
    }
    
    # 1. Update JSON (for internal tracking if needed)
    with _log_lock:
        data = []
        if USAGE_LOG_PATH.exists():
            try:
                data = json.loads(USAGE_LOG_PATH.read_text(encoding="utf-8"))
            except:
                data = []
        data.append(usage)
        USAGE_LOG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        # 2. Update Markdown Report (User facing)
        header = (
            "# Subtitle Forge - Pipeline Usage Report\n\n"
            "| Time | Category | Activity Detail | Input | Output | Total | Est. Cost |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        )
        existing = USAGE_MD_PATH.read_text(encoding="utf-8") if USAGE_MD_PATH.exists() else ""
        if "| Time |" not in existing:
            existing = header
        row = f"| {timestamp} | **{category}** | {detail} | {input_tokens:,} | {output_tokens:,} | {total_tokens:,} | ${cost:.4f} |\n"
        USAGE_MD_PATH.write_text(existing + row, encoding="utf-8")

def get_total_usage():
    """Summary of all usage from JSON."""
    if not USAGE_LOG_PATH.exists():
        return {}
    
    try:
        data = json.loads(USAGE_LOG_PATH.read_text(encoding="utf-8"))
    except:
        return {}
        
    totals = {
        "input": sum(u["input_tokens"] for u in data),
        "output": sum(u["output_tokens"] for u in data),
        "total": sum(u["total_tokens"] for u in data),
        "cost": sum(u["estimated_cost_usd"] for u in data)
    }
    return totals
def log_failure(stage: str, context: str, error: str):
    """Log a pipeline failure to a Markdown file in a thread-safe manner."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    header = (
        "# Subtitle Forge - Pipeline Failure Report\n\n"
        "| Time | Stage | Context | Error Message |\n"
        "| :--- | :--- | :--- | :--- |\n"
    )
    with _log_lock:
        existing = FAILURE_MD_PATH.read_text(encoding="utf-8") if FAILURE_MD_PATH.exists() else ""
        if "| Time |" not in existing:
            existing = header
        
        # Escape pipe characters for markdown table
        error_clean = error.replace("|", "\\|").replace("\n", " ")
        row = f"| {timestamp} | **{stage}** | {context} | {error_clean} |\n"
        FAILURE_MD_PATH.write_text(existing + row, encoding="utf-8")
    
    print(f"  [Error] Logged to {FAILURE_MD_PATH.name}")
