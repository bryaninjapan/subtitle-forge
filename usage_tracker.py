import json
import time
from pathlib import Path
from config import BASE_DIR

USAGE_LOG_PATH = BASE_DIR / "usage_log.json"
USAGE_MD_PATH = BASE_DIR / "pipeline_report.md"

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
