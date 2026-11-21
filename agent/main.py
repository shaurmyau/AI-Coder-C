import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite import SqliteSaver

from agent.config import LOG_DIR, PROJECT_ROOT, WORKSPACE
from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOLS

load_dotenv(PROJECT_ROOT / ".env", override=False)

MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
MAX_STEPS = int(os.getenv("MAX_AGENT_STEPS", "80"))
NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "24576"))

logging.basicConfig(
    filename=str(LOG_DIR / "agent.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8",
)


def build_agent(checkpointer):
    llm = ChatOllama(
        model=MODEL,
        base_url=BASE_URL,
        temperature=0.2,
        num_ctx=NUM_CTX,
    )
    return create_agent(
        model=llm,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
        name="AI_Game_Developer",
    )


def print_tool_activity(messages):
    for message in messages:
        if getattr(message, "type", "") == "tool":
            print(f"\n[TOOL: {message.name}]")
            print(str(message.content)[:1600])
            logging.info("TOOL %s", message.name)


def main():
    print("=" * 68)
    print("             AI GAME DEVELOPER — C++ EDITION")
    print("=" * 68)
    print(f"Model: {MODEL}")
    print(f"Ollama: {BASE_URL}")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Workspace: {WORKSPACE}")
    print("Stack: C++20 | MSVC x64 | CMake | vcpkg | SFML 3")
    print("Memory: SQLite")
    print("\nCommands: /new — new conversation | /exit — quit")
    print("=" * 68)

    db_path = LOG_DIR / "memory.sqlite"
    with SqliteSaver.from_conn_string(str(db_path)) as memory:
        agent = build_agent(memory)
        thread_id = "main"

        while True:
            try:
                task = input("\nYOU > ").strip()
                if not task:
                    continue
                if task.lower() == "/exit":
                    break
                if task.lower() == "/new":
                    thread_id = str(uuid.uuid4())
                    print("Создан новый диалог:", thread_id)
                    continue

                logging.info("USER TASK: %s", task[:1000])
                print("\nAI GAME DEVELOPER > Выполняю задачу...\n")
                result = agent.invoke(
                    {"messages": [{"role": "user", "content": task}]},
                    config={
                        "configurable": {"thread_id": thread_id},
                        "recursion_limit": MAX_STEPS,
                    },
                )
                messages = result["messages"]
                print_tool_activity(messages)
                final_message = next(
                    (
                        message for message in reversed(messages)
                        if getattr(message, "type", "") == "ai"
                        and not getattr(message, "tool_calls", [])
                    ),
                    messages[-1],
                )
                print("\n" + "=" * 68)
                print("RESULT")
                print("=" * 68)
                print(final_message.content)
                logging.info("TASK COMPLETED")
            except KeyboardInterrupt:
                print("\nПрервано пользователем.")
            except Exception as exc:
                logging.exception("AGENT ERROR")
                print("\nОШИБКА:", exc)


if __name__ == "__main__":
    main()
