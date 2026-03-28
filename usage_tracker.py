import json
import time
import threading
import sys
from pathlib import Path
from config import (  # type: ignore
    BASE_DIR, 
    COST_INPUT_FLASH, COST_OUTPUT_FLASH,
    COST_INPUT_LITE, COST_OUTPUT_LITE
)

USAGE_LOG_PATH = BASE_DIR / "usage_log.jsonl"
USAGE_MD_PATH = BASE_DIR / "pipeline_report.md"
FAILURE_MD_PATH = BASE_DIR / "pipeline_failures.md"

_log_lock = threading.Lock()
_backoff_until = 0.0
_backoff_lock = threading.Lock()

def signal_backoff(seconds: float = 30.0):
    global _backoff_until
    with _backoff_lock:
        target = time.time() + seconds
        if target > _backoff_until:
            _backoff_until = target
            print(f"\n⚠️  [Backoff] Throttling for {seconds:.0f}s...")

def check_backoff():
    global _backoff_until
    while True:
        wait = _backoff_until - time.time()
        if wait <= 0: break
        time.sleep(min(wait, 2.0))

def check_cost_cap():
    """Verify if total cost exceeds settings.yaml max_cost_usd."""
    from config import MAX_COST_USD  # type: ignore
    if MAX_COST_USD <= 0: return
    usage = get_total_usage()
    if usage.get("cost", 0.0) >= MAX_COST_USD:
        print(f"\n🛑 [STOP] Cost Cap Reached: ${usage['cost']:.4f} >= ${MAX_COST_USD:.4f}")
        sys.exit(0)

def estimate_cost(duration_min: float, model: str = "gemini-2.5-flash") -> float:
    if "flash-8b" in model:
        in_c, out_c = COST_INPUT_LITE, COST_OUTPUT_LITE
    else:
        in_c, out_c = COST_INPUT_FLASH, COST_OUTPUT_FLASH
    return (duration_min * 1920 / 1e6 * in_c) + (duration_min * 1800 / 1e6 * (in_c + out_c))

def log_usage(category: str, detail: str, input_tokens: int, output_tokens: int, model: str = "gemini-2.5-flash"):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    if ":free" in model:
        cost = 0.0
    elif "flash-8b" in model:
        in_c, out_c = COST_INPUT_LITE, COST_OUTPUT_LITE
        cost = (input_tokens * (in_c / 1e6)) + (output_tokens * (out_c / 1e6))
    else:
        in_c, out_c = COST_INPUT_FLASH, COST_OUTPUT_FLASH
        cost = (input_tokens * (in_c / 1e6)) + (output_tokens * (out_c / 1e6))
    usage = {
        "timestamp": timestamp, "category": category, "detail": detail,
        "input": input_tokens, "output": output_tokens, "model": model, "cost": cost
    }
    
    with _log_lock:
        with open(USAGE_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(usage, ensure_ascii=False) + "\n")

        if not USAGE_MD_PATH.exists():
            header = "# Pipeline Report\n\n| Time | Cat | Detail | In | Out | Model | Cost |\n|:---|:---|:---|:---|:---|:---|:---|\n"
            USAGE_MD_PATH.write_text(header, encoding="utf-8")
        
        row = f"| {timestamp} | {category} | {detail} | {input_tokens:,} | {output_tokens:,} | {model} | ${cost:.4f} |\n"
        with open(USAGE_MD_PATH, "a", encoding="utf-8") as f: f.write(row)
    
    # Check cap after each log
    check_cost_cap()

def get_total_usage():
    if not USAGE_LOG_PATH.exists(): return {"cost": 0.0, "input": 0, "output": 0}
    data = []
    with open(USAGE_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip(): data.append(json.loads(line))
    return {
        "input": sum(u.get("input", 0) for u in data),
        "output": sum(u.get("output", 0) for u in data),
        "cost": sum(u.get("cost", 0.0) for u in data)
    }

def log_failure(stage: str, context: str, error: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with _log_lock:
        if not FAILURE_MD_PATH.exists():
            FAILURE_MD_PATH.write_text("# Failure Report\n\n| Time | Stage | Context | Error |\n|:---|:---|:---|:---|\n", encoding="utf-8")
        err_c = error.replace("|", "\\|").replace("\n", " ")
        with open(FAILURE_MD_PATH, "a", encoding="utf-8") as f:
            f.write(f"| {timestamp} | {stage} | {context} | {err_c} |\n")
