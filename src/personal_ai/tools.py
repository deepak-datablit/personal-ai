"""Tools: read_file, write_file, search_files, exec_command, update_user_profile, browse + OpenAI schemas."""
import re
import subprocess
import yaml
from pathlib import Path
from urllib.parse import urlparse

import html2text
from playwright.sync_api import sync_playwright

from .workspace import WORKSPACE_DIR, USER_MEMORY_FILE

# Project root = directory containing src/, workspace/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MAX_FILE_SIZE = 512 * 1024  # 512 KiB
EXEC_TIMEOUT = 60
USER_MEMORY_PATH = WORKSPACE_DIR / USER_MEMORY_FILE

# Browser tool
BROWSE_TIMEOUT_MS = 30_000
BROWSE_DEFAULT_WAIT_MS = 2_000
BROWSE_MAX_TEXT_CHARS = 80_000


def browse(
    url: str,
    wait_selector: str | None = None,
    wait_time_ms: int | None = None,
    max_text_chars: int | None = None,
) -> str:
    """Fetch a webpage with Playwright and return its content as readable text.

    Use for any website: Google search, Reddit, news, etc. For large pages, HTML
    is converted to text via html2text and truncated to stay within limits.

    - url: Full URL to open (e.g. https://www.google.com/search?q=reddit).
    - wait_selector: Optional CSS selector to wait for before capturing (e.g. "#content").
    - wait_time_ms: Optional extra wait in ms after load (default 2000).
    - max_text_chars: Max length of returned text (default 80000).
    """
    if not url or not url.strip():
        return "Error: url is required."
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return "Error: invalid url."
    except Exception:
        return "Error: invalid url."

    timeout = BROWSE_TIMEOUT_MS
    wait_ms = wait_time_ms if wait_time_ms is not None else BROWSE_DEFAULT_WAIT_MS
    max_chars = max_text_chars if max_text_chars is not None else BROWSE_MAX_TEXT_CHARS

    try:
        with sync_playwright() as p:
            # Use installed Chrome if available; otherwise Playwright's Chromium
            try:
                browser = p.chromium.launch(headless=True, channel="chrome")
            except Exception:
                browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                if wait_selector:
                    page.wait_for_selector(wait_selector, timeout=timeout)
                page.wait_for_timeout(wait_ms)
                html = page.content()
            finally:
                browser.close()
    except Exception as e:
        err = str(e).lower()
        if "executable" in err or "browser" in err or "chromium" in err or "channel" in err:
            return f"Error loading page: {e}. Install Chrome or run: playwright install chromium"
        return f"Error loading page: {e}"

    try:
        h2t = html2text.HTML2Text()
        h2t.ignore_links = False
        h2t.ignore_images = True
        h2t.body_width = 0
        text = h2t.handle(html)
    except Exception as e:
        return f"Error converting HTML to text: {e}"

    text = text.strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... truncated for length ...]"
    return text or "(no text content)"


def _resolve_path(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    try:
        return p.resolve().relative_to(PROJECT_ROOT)
    except ValueError:
        raise ValueError(f"Path must be under project root: {path}")


def read_file(path: str) -> str:
    p = _resolve_path(path)
    full = PROJECT_ROOT / p
    if not full.is_file():
        return f"Error: not a file or not found: {path}"
    if full.stat().st_size > MAX_FILE_SIZE:
        return f"Error: file too large (max {MAX_FILE_SIZE} bytes)"
    return full.read_text(encoding="utf-8", errors="replace")


def write_file(path: str, content: str) -> str:
    p = _resolve_path(path)
    full = PROJECT_ROOT / p
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} bytes to {path}"


def search_files(directory: str, pattern: str) -> str:
    try:
        base = _resolve_path(directory)
    except ValueError:
        return f"Error: directory must be under project: {directory}"
    root = PROJECT_ROOT / base
    if not root.is_dir():
        return f"Error: not a directory: {directory}"
    out = []
    try:
        re_pat = re.compile(pattern, re.IGNORECASE)
    except re.error:
        return f"Error: invalid regex pattern: {pattern}"
    for f in root.rglob("*"):
        if f.is_file() and f.stat().st_size <= MAX_FILE_SIZE:
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                if re_pat.search(text):
                    rel = f.relative_to(PROJECT_ROOT)
                    out.append(f"{rel}: (match)")
            except Exception:
                pass
    if not out:
        return "No matches found."
    return "\n".join(out[:50])


def exec_command(command: str) -> str:
    try:
        r = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=EXEC_TIMEOUT,
            cwd=PROJECT_ROOT,
        )
        out = (r.stdout or "").strip() or "(no stdout)"
        err = (r.stderr or "").strip()
        if err:
            out += "\nstderr: " + err
        if r.returncode != 0:
            out += f"\nExit code: {r.returncode}"
        return out
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {EXEC_TIMEOUT}s"
    except Exception as e:
        return f"Error: {e}"

def _to_snake_case(s: str) -> str:
    """Normalize key to snake_case: lowercase, spaces/hyphens -> underscores."""
    s = s.strip().lower().replace(" ", "_").replace("-", "_")
    return re.sub(r"_+", "_", s).strip("_")


def update_user_profile(updates: dict | None = None) -> str:
    """Update long-term memory (user_memory.yaml). Keys are stored in snake_case. Pass key: value; existing keys updated, new keys appended."""
    if not updates or not isinstance(updates, dict):
        return "Error: provide 'updates' (object of key: value)."
    USER_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        raw = USER_MEMORY_PATH.read_text(encoding="utf-8")
        data = yaml.safe_load(raw) if raw.strip() else {}
    except FileNotFoundError:
        data = {}
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}

    def find_key(d: dict, key: str) -> str | None:
        norm = _to_snake_case(key)
        for k in d:
            if _to_snake_case(k) == norm:
                return k
        return None

    updated = []
    for key, raw_val in updates.items():
        if raw_val is None or (isinstance(raw_val, str) and not raw_val.strip()):
            continue
        value = str(raw_val).strip().replace("\n", " ")
        snake = _to_snake_case(key)
        if not snake:
            continue
        existing = find_key(data, key)
        if existing is not None:
            del data[existing]
        data[snake] = value
        updated.append(snake)

    if not updated:
        return "Error: no valid key: value pairs in 'updates'."

    try:
        USER_MEMORY_PATH.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return f"Updated: {', '.join(updated)}"
    except Exception as e:
        return f"Error: {e}"


TOOL_IMPLEMENTATIONS = {
    "read_file": read_file,
    "write_file": write_file,
    "search_files": search_files,
    "exec_command": exec_command,
    "update_user_profile": update_user_profile,
    "browse": browse,
}

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file. Path is relative to project root or absolute.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "File path"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Path under project root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for a regex pattern in files under a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Directory path under project"},
                    "pattern": {"type": "string", "description": "Regex pattern to search"},
                },
                "required": ["directory", "pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "exec_command",
            "description": "Run a shell command. Use with care.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_user_profile",
            "description": "Update long-term user memory (user_memory.yaml). You MUST call this whenever the user shares their name, interests, hobbies, preferences, timezone, or any other personal fact — e.g. on first meeting or when they say what they like or use. Call it in the same turn so future replies can personalize. Use snake_case keys only (e.g. name, interests, favorite_language, timezone). Pass updates: { \"key\": \"value\" }. Existing keys updated; new keys appended.",
            "parameters": {
                "type": "object",
                "properties": {
                    "updates": {
                        "type": "object",
                        "description": "Keys must be snake_case (e.g. name, interests, favorite_language, what_to_call_them, timezone). Values are strings. Extract from the user message.",
                        "additionalProperties": {"type": "string"},
                    },
                },
                "required": ["updates"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browse",
            "description": "Fetch a webpage and return its content as readable text. Use for any site. Reddit: for 'my Reddit feed' or 'summary of my Reddit', if you know the user's Reddit username (from memory key reddit_username or from the conversation), call with url https://www.reddit.com/user/USERNAME/ and summarize. Save reddit_username via update_user_profile when the user shares it. For subreddits use https://reddit.com/r/SUBREDDIT. Google: https://www.google.com/search?q=QUERY. Gmail/mail: gmail.com (requires logged-in session). HTML is converted to text; large pages are truncated.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL to open (e.g. https://www.google.com/search?q=reddit or https://reddit.com)"},
                    "wait_selector": {"type": "string", "description": "Optional CSS selector to wait for before capturing content"},
                    "wait_time_ms": {"type": "integer", "description": "Optional extra wait in milliseconds after load (default 2000)"},
                    "max_text_chars": {"type": "integer", "description": "Optional max length of returned text (default 80000)"},
                },
                "required": ["url"],
            },
        },
    },
]
