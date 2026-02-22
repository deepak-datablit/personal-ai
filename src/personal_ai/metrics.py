"""LLM token metrics: total (global) and per-session, stored in workspace/metrics/."""
import json
from pathlib import Path

from .workspace import WORKSPACE_DIR

METRICS_DIR = WORKSPACE_DIR / "metrics"
TOTAL_FILE = METRICS_DIR / "total.json"


def ensure_metrics_dir() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)


def _read_counts(path: Path) -> dict[str, int]:
    """Read JSON file with input_tokens, output_tokens, total_tokens; return zeros if missing."""
    if not path.exists():
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "input_tokens": int(data.get("input_tokens", 0)),
            "output_tokens": int(data.get("output_tokens", 0)),
            "total_tokens": int(data.get("total_tokens", 0)),
        }
    except (json.JSONDecodeError, OSError):
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def _write_counts(path: Path, counts: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(counts, indent=2), encoding="utf-8")


def record_usage(
    session_path: Path | None,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Record token usage: update global total and, if session_path given, session file.

    - Total: workspace/metrics/total.json (cumulative across all sessions).
    - Session: workspace/metrics/<session_stem>.json (e.g. session_2026-02-23T01-26-44.json).
    """
    ensure_metrics_dir()
    total = input_tokens + output_tokens

    # Update total
    counts = _read_counts(TOTAL_FILE)
    counts["input_tokens"] += input_tokens
    counts["output_tokens"] += output_tokens
    counts["total_tokens"] += total
    _write_counts(TOTAL_FILE, counts)

    # Update session file if provided
    if session_path is not None:
        session_file = METRICS_DIR / f"{session_path.stem}.json"
        counts = _read_counts(session_file)
        counts["input_tokens"] += input_tokens
        counts["output_tokens"] += output_tokens
        counts["total_tokens"] += total
        _write_counts(session_file, counts)


def get_total_usage() -> dict[str, int]:
    """Return cumulative token counts across all sessions."""
    ensure_metrics_dir()
    return _read_counts(TOTAL_FILE)


def get_session_usage(session_path: Path) -> dict[str, int]:
    """Return token counts for the given session file."""
    session_file = METRICS_DIR / f"{session_path.stem}.json"
    return _read_counts(session_file)
