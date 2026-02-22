"""Workspace memory: user_memory.yaml (long-term memory), AGENT.md."""
import os
import yaml
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project root = parent of src/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
# Workspace dir: from .env WORKSPACE_PATH, or default <project>/workspace
_workspace_path = (os.getenv("WORKSPACE_PATH") or "").strip()
WORKSPACE_DIR = Path(_workspace_path).resolve() if _workspace_path else _PROJECT_ROOT / "workspace"
USER_MEMORY_FILE = "user_memory.yaml"
FILES = (USER_MEMORY_FILE, "AGENT.md")

DEFAULTS = {
    USER_MEMORY_FILE: "",
    "AGENT.md": """# Agent rules

## User memory (YAML above)

- **Use it** — The "User:" YAML block above is long-term memory. Use it to personalize replies.
- **Keys: snake_case** — All keys are snake_case (e.g. name, what_to_call_them, timezone). Use snake_case when updating.
- **Update it (required)** — Whenever the user shares any personal fact or preference (name, interests, hobbies, favorites, timezone), you must call update_user_profile in the same turn with updates: { "snake_case_key": "value" }. Do not skip this when the user introduces themselves or shares preferences.

**Reply** — Never mention saving, profile, or memory. Answer naturally.
""",
}


def ensure_workspace() -> None:
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        p = WORKSPACE_DIR / name
        if not p.exists():
            p.write_text(DEFAULTS[name], encoding="utf-8")


def load_user_memory_yaml() -> str:
    """Load user memory as compact YAML string for system prompt (low token use)."""
    p = WORKSPACE_DIR / USER_MEMORY_FILE
    if not p.exists():
        return ""
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception:
        return ""
    if not data or not isinstance(data, dict):
        return ""
    clean = {k: str(v).strip() for k, v in data.items() if v is not None and str(v).strip()}
    if not clean:
        return ""
    return yaml.dump(clean, default_flow_style=False, allow_unicode=True, sort_keys=False)


def load_system_prompt() -> str:
    """Build system prompt: user memory (YAML) + AGENT.md. Compact for fewer tokens."""
    ensure_workspace()
    parts = []
    user_yaml = load_user_memory_yaml()
    if user_yaml:
        parts.append("User:\n" + user_yaml.strip())
    agent_path = WORKSPACE_DIR / "AGENT.md"
    if agent_path.exists():
        parts.append(agent_path.read_text(encoding="utf-8"))
    return "\n\n".join(parts)
