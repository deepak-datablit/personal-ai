"""Structured logging: one file per day (agent_YYYY-MM-DD.log) in workspace/logs/."""
import json
import uuid
from datetime import datetime
from pathlib import Path

from .workspace import WORKSPACE_DIR

LOG_DIR = WORKSPACE_DIR / "logs"

_request_id: str | None = None


def _log_file_for_today() -> Path:
    """Path to today's log file: workspace/logs/agent_YYYY-MM-DD.log (local date)."""
    today = datetime.now().strftime("%Y-%m-%d")
    return LOG_DIR / f"agent_{today}.log"


def ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def set_request_id(rid: str | None = None) -> str:
    global _request_id
    _request_id = rid or str(uuid.uuid4())
    return _request_id


def get_request_id() -> str | None:
    return _request_id


def _emit(event: str, payload: object) -> None:
    ensure_log_dir()
    log_file = _log_file_for_today()
    record = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "request_id": get_request_id() or "",
        "event": event,
        "payload": payload,
    }
    line = json.dumps(record, default=str, ensure_ascii=False) + "\n"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)


def log_llm_request(model: str, messages: list[dict]) -> None:
    """Log full LLM request with model and messages array."""
    _emit("llm_request", {"model": model, "message_count": len(messages), "messages": messages})


def log_llm_response(response_message: dict, tool_calls_count: int) -> None:
    """Log full LLM response message."""
    _emit("llm_response", {
        "content_len": len(response_message.get("content") or ""),
        "tool_calls_count": tool_calls_count,
        "message": response_message,
    })


def log_tool_call(name: str, arguments: object) -> None:
    _emit("tool_call", {"name": name, "arguments": arguments})


def log_tool_result(name: str, result: str) -> None:
    _emit("tool_result", {"name": name, "result": result})
