"""
history.py — Download history and debug logging for The Dracula CLI & TUI.
Log entries stored in ~/.config/dracula/history.jsonl
Debug messages logged to ~/.config/dracula/debug.log
"""

import json
import time
from datetime import datetime
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "dracula"
HISTORY_FILE = CONFIG_DIR / "history.jsonl"
DEBUG_FILE = CONFIG_DIR / "debug.log"


def log_debug(msg: str, exception: Exception | str | None = None):
    """Log swallowed exception or debug message to ~/.config/dracula/debug.log."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        err_str = f" | Exception: {exception}" if exception else ""
        with open(DEBUG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {msg}{err_str}\n")
    except Exception:
        pass


def add_history_entry(
    title: str,
    url: str,
    format_str: str,
    quality_or_bitrate: str,
    output_path: str,
    status: str = "success",
    error: str | None = None,
):
    """Append a download record to history.jsonl."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        record = {
            "title": title or "Unknown Title",
            "url": url or "",
            "format": format_str or "unknown",
            "quality_or_bitrate": quality_or_bitrate or "default",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "output_path": output_path or "",
            "status": status,
            "error": error,
        }
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        log_debug(f"Failed to write history entry for {url}", e)


def read_history(limit: int = 50) -> tuple[list[dict], int]:
    """Read history log entries, returning (recent_entries, total_count).

    Returned entries are sorted most recent first.
    """
    entries = []
    if not HISTORY_FILE.exists():
        return [], 0

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        log_debug("Failed to read history log", e)
        return [], 0

    total_count = len(entries)
    # Reverse so most recent comes first
    entries.reverse()
    if limit and limit > 0:
        entries = entries[:limit]

    return entries, total_count
