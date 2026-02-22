"""CLI entrypoint: REPL, one session per run, load context, run agent, save session."""
import os
import uuid
from dotenv import load_dotenv

from . import log_utils
from . import session
from . import workspace
from . import agent

load_dotenv()


def main() -> None:
    log_utils.ensure_log_dir()
    api_key = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Set LLM_API_KEY (or GEMINI_API_KEY) in .env")
        return
    client = agent.create_client(api_key)
    session_path = session.start_session()
    history = session.load_history(session_path)
    print(f"Session: {session_path.name}")
    print('Say "exit" or "quit" to end.\n')

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break
        request_id = str(uuid.uuid4())
        system_prompt = workspace.load_system_prompt()
        reply, to_append = agent.chat(
            client, system_prompt, history, user_input, request_id, session_path
        )
        session.append_messages(session_path, to_append)
        history.extend(to_append)
        print(f"Agent: {reply}\n")


if __name__ == "__main__":
    main()
