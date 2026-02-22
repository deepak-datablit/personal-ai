"""Agent: system prompt + history, agentic loop with tool execution and structured logging."""
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

from . import log_utils
from . import metrics
from .workspace import load_system_prompt
from .tools import TOOL_IMPLEMENTATIONS, OPENAI_TOOLS

load_dotenv()
MODEL = os.getenv("LLM_MODEL", "")
BASE_URL = os.getenv("LLM_BASE_URL", "")


def run_tool(name: str, arguments: dict) -> str:
    impl = TOOL_IMPLEMENTATIONS.get(name)
    if not impl:
        return f"Error: unknown tool {name}"
    log_utils.log_tool_call(name, arguments)
    try:
        if name == "update_user_profile":
            result = impl(updates=arguments.get("updates"))
        elif name == "read_file":
            result = impl(arguments["path"])
        elif name == "write_file":
            result = impl(arguments["path"], arguments["content"])
        elif name == "search_files":
            result = impl(arguments["directory"], arguments["pattern"])
        elif name == "exec_command":
            result = impl(arguments["command"])
        else:
            result = impl(**arguments)
    except Exception as e:
        result = f"Error: {e}"
    log_utils.log_tool_result(name, result)
    return result


def chat(
    client: OpenAI,
    system_prompt: str,
    history: list[dict],
    user_message: str,
    request_id: str,
    session_path: Path | None = None,
) -> tuple[str, list[dict]]:
    """Run agentic loop. Returns (final_assistant_text, messages_to_append_to_session)."""
    log_utils.set_request_id(request_id)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    to_append = [{"role": "user", "content": user_message}]

    while True:
        log_utils.log_llm_request(MODEL, messages)
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=OPENAI_TOOLS,
        )
        if getattr(resp, "usage", None) is not None:
            u = resp.usage
            metrics.record_usage(
                session_path,
                getattr(u, "prompt_tokens", 0) or getattr(u, "input_tokens", 0),
                getattr(u, "completion_tokens", 0) or getattr(u, "output_tokens", 0),
            )
        choice = resp.choices[0]
        msg = choice.message
        tool_calls = getattr(msg, "tool_calls", None) or []

        response_msg = {"role": "assistant", "content": msg.content}
        if tool_calls:
            response_msg["tool_calls"] = [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ]
        log_utils.log_llm_response(response_msg, len(tool_calls))
        if not tool_calls:
            final = (msg.content or "").strip()
            to_append.append({"role": "assistant", "content": final})
            return final, to_append

        assistant_msg = {"role": "assistant", "content": msg.content, "tool_calls": []}
        for tc in tool_calls:
            assistant_msg["tool_calls"].append(
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            )
        messages.append(assistant_msg)
        to_append.append(assistant_msg)

        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            result = run_tool(name, args)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            to_append.append({"role": "tool", "tool_call_id": tc.id, "content": result})


def create_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=BASE_URL)
