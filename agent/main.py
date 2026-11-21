import os
import uuid
import logging
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite import SqliteSaver

from agent.tools import TOOLS
from agent.prompts import SYSTEM_PROMPT

ROOT = Path(r"D:\AI-Coder-C++")
load_dotenv(ROOT / ".env")

os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

logging.basicConfig(
    filename=str(ROOT / "logs" / "agent.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)

MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
MAX_STEPS = int(os.getenv("MAX_AGENT_STEPS", "60"))


def build_agent(checkpointer):
    llm = ChatOllama(
        model=MODEL,
        base_url=BASE_URL,
        temperature=0.2,
        num_ctx=16384
    )

    return create_agent(
        model=llm,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
        name="AI_Coder_Pro"
    )


def print_tool_activity(messages):
    for message in messages:
        if getattr(message, "type", "") == "tool":
            print(f"\n[TOOL: {message.name}]")
            print(str(message.content)[:1200])
            logging.info("TOOL %s", message.name)


def main():
    print("=" * 65)
    print("                 AI CODER PRO v2")
    print("=" * 65)
    print("Model:", MODEL)
    print("Ollama:", BASE_URL)
    print("Workspace:", ROOT / "workspace")
    print("Persistent memory: SQLite")
    print()
    print("РљРѕРјР°РЅРґС‹:")
    print("/new    - РЅР°С‡Р°С‚СЊ РЅРѕРІС‹Р№ РґРёР°Р»РѕРі")
    print("/exit   - РІС‹С…РѕРґ")
    print("=" * 65)

    db_path = ROOT / "logs" / "memory.sqlite"

    with SqliteSaver.from_conn_string(str(db_path)) as memory:
        agent = build_agent(memory)

        # РџРѕСЃС‚РѕСЏРЅРЅС‹Р№ ID РїРѕР·РІРѕР»СЏРµС‚ РїСЂРѕРґРѕР»Р¶Р°С‚СЊ РґРёР°Р»РѕРі РїРѕСЃР»Рµ РїРµСЂРµР·Р°РїСѓСЃРєР°.
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
                    print("РЎРѕР·РґР°РЅ РЅРѕРІС‹Р№ РґРёР°Р»РѕРі:", thread_id)
                    continue

                print("\nAI CODER > Р’С‹РїРѕР»РЅСЏСЋ Р·Р°РґР°С‡Сѓ...\n")
                logging.info("USER TASK: %s", task[:1000])

                result = agent.invoke(
                    {
                        "messages": [
                            {"role": "user", "content": task}
                        ]
                    },
                    config={
                        "configurable": {"thread_id": thread_id},
                        "recursion_limit": MAX_STEPS
                    }
                )

                messages = result["messages"]
                print_tool_activity(messages)

                final_message = next(
                    (
                        message for message in reversed(messages)
                        if getattr(message, "type", "") == "ai"
                        and not getattr(message, "tool_calls", [])
                    ),
                    messages[-1]
                )

                print("\n" + "=" * 65)
                print("AI CODER PRO RESULT")
                print("=" * 65)
                print(final_message.content)

                logging.info("TASK COMPLETED")

            except KeyboardInterrupt:
                print("\nРџСЂРµСЂРІР°РЅРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»РµРј.")

            except Exception as exc:
                logging.exception("AGENT ERROR")
                print("\nРћРЁРР‘РљРђ:", exc)


if __name__ == "__main__":
    main()
