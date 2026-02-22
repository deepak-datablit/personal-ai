"""Session: one JSONL file per run; append messages, load history."""
import json
from pathlib import Path
from datetime import datetime, timezone

from .workspace import WORKSPACE_DIR

SESSIONS_DIR = WORKSPACE_DIR / "sessions"


def ensure_sessions_dir() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def start_session() -> Path:
    ensure_sessions_dir()
    ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    path = SESSIONS_DIR / f"session_{ts}.jsonl"
    path.touch()
    return path


def load_history(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def append_messages(path: Path, messages: list[dict]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for m in messages:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
