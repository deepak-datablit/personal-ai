# Personal AI Agent MVP

CLI personal AI agent: chat with an LLM (Gemini 2.0 Flash via OpenAI-compatible API), tools (file read/write/search, exec, update_user_profile), long-term memory in `workspace/user_memory.yaml` (YAML), sessions and logs under `workspace/`.

## Project layout

```
personal-ai/
├── src/personal_ai/   # all Python code
├── workspace/        # data: user_memory.yaml, AGENT.md, logs/, sessions/
│   ├── logs/          # agent_YYYY-MM-DD.log (one file per day)
│   └── sessions/      # session_*.jsonl
├── pyproject.toml
└── .env
```

## Setup (uv)

1. Install [uv](https://docs.astral.sh/uv/).
2. From the project root:
   ```bash
   uv venv
   uv pip install -e .
   ```
   On Windows with venv activated: `.venv\Scripts\activate` then `uv pip install -e .`
3. Copy `.env.example` to `.env` and set your API key (and optionally `WORKSPACE_PATH`):
   ```
   GEMINI_API_KEY=your_key_here
   # WORKSPACE_PATH=./workspace   # optional; default is <project_root>/workspace
   ```
   Get a key at [Google AI Studio](https://aistudio.google.com/apikey).

## Run

From the project root (after `uv pip install -e .`):

```bash
python -m personal_ai.main
```

Or: `personal-ai`

Say `exit` or `quit` to end. Sessions and logs go to `workspace/sessions/` and `workspace/logs/`. User memory (YAML) and AGENT.md are loaded each turn; the agent updates memory via `update_user_profile` (key: value).

## Plan

See [PLAN.md](PLAN.md) for the implementation plan.
