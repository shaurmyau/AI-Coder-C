import logging
import os
import re
import uuid
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite import SqliteSaver

from agent.config import LOG_DIR, PROJECT_ROOT, WORKSPACE
from agent.environment import check_ollama_service, check_environment_report
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


def is_environment_check_request(task: str) -> bool:
    """Detect simple environment/version diagnostics that should bypass the LLM."""
    normalized = " ".join(
        task.casefold().replace("ё", "е").split()
    )

    actions = (
        "проверь",
        "проверить",
        "проверка",
        "проведи проверку",
        "покажи",
        "узнай",
        "определи",
    )

    targets = (
        "верс",
        "библиотек",
        "зависимост",
        "окружен",
    )

    modifying_actions = (
        "обнов",
        "установ",
        "удал",
        "исправ",
        "переустанов",
        "собери",
    )

    has_action = any(word in normalized for word in actions)
    has_target = any(word in normalized for word in targets)
    has_modification = any(word in normalized for word in modifying_actions)

    return has_action and has_target and not has_modification


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


def run_direct_environment_check():
    """Run environment diagnostics without model reasoning or tool-calling loops."""
    print("\n[ENVIRONMENT] Запускаю непосредственную проверку окружения...\n")

    report = check_environment_report(".")

    print("=" * 68)
    print("РЕЗУЛЬТАТ ПРОВЕРКИ ОКРУЖЕНИЯ")
    print("=" * 68)
    print(report)
    print("=" * 68)

    logging.info("DIRECT ENVIRONMENT CHECK COMPLETED")


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
    print("\nCommands: /new — new conversation | /check-env — check environment | /exit — quit")
    print("=" * 68)

    service_ok, service_message = check_ollama_service(BASE_URL, MODEL)
    print("\n[PRE-FLIGHT]", service_message)

    if not service_ok:
        print("Агент не запущен: сначала запусти Ollama и проверь OLLAMA_BASE_URL в .env.")
        return

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

                if task.lower() == "/check-env" or is_environment_check_request(task):
                    logging.info("DIRECT ENVIRONMENT CHECK: %s", task[:1000])

                    try:
                        run_direct_environment_check()
                    except Exception as exc:
                        logging.exception("ENVIRONMENT CHECK ERROR")
                        print("\nОШИБКА ПРОВЕРКИ ОКРУЖЕНИЯ:", exc)

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