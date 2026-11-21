"""Interactive entry point for the AI Coder agent."""

import logging
import os
import uuid
from time import perf_counter

from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite import SqliteSaver

from agent.config import LOG_DIR, PROJECT_ROOT, WORKSPACE, ensure_directories
from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOLS


os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")
ensure_directories()

MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
MAX_STEPS = int(os.getenv("MAX_AGENT_STEPS", "60"))
NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "16384"))

logging.basicConfig(
    filename=str(LOG_DIR / "agent.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8",
)


def build_agent(checkpointer):
    """Create the LangGraph agent with the configured Ollama model."""
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
        name="AI_Coder_Pro",
    )


def message_text(message) -> str:
    """Convert common LangChain message content shapes into printable text."""
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        pieces = []
        for block in content:
            if isinstance(block, str):
                pieces.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                pieces.append(block["text"])
        return "".join(pieces)
    return str(content) if content else ""


def print_tool_message(message) -> None:
    """Print and log a completed tool result."""
    name = getattr(message, "name", "unknown")
    content = message_text(message)
    print(f"\n[TOOL: {name}]")
    print(content[:1600] if content else "(инструмент не вернул текстовый вывод)")
    logging.info("TOOL %s: %s", name, content[:4000])


def _final_ai_message(messages):
    for message in reversed(messages):
        if (
            getattr(message, "type", "") == "ai"
            and not getattr(message, "tool_calls", [])
        ):
            return message
    return None


def stream_agent_response(agent, task: str, thread_id: str):
    """Run the graph with live step/tool activity and return its final AI message."""
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": MAX_STEPS,
    }
    collected_messages = []
    model_activity_announced = False
    model_chunks = 0
    started_at = perf_counter()

    # The v1 tuple format is supported by LangGraph's long-standing stream API.
    for mode, chunk in agent.stream(
        {"messages": [{"role": "user", "content": task}]},
        config=config,
        stream_mode=["messages", "updates"],
    ):
        if mode == "messages":
            message, metadata = chunk
            if metadata.get("langgraph_node") == "model":
                model_chunks += 1
                if not model_activity_announced:
                    print("[MODEL] Модель начала генерировать ответ.")
                    model_activity_announced = True
                elif model_chunks % 100 == 0:
                    print(f"[MODEL] Получено фрагментов: {model_chunks}", flush=True)
            continue

        if mode != "updates" or not isinstance(chunk, dict):
            continue

        for node_name, node_update in chunk.items():
            if not isinstance(node_update, dict):
                continue

            new_messages = node_update.get("messages", [])
            if not isinstance(new_messages, list):
                continue

            for message in new_messages:
                collected_messages.append(message)
                message_type = getattr(message, "type", "")

                if message_type == "ai":
                    for tool_call in getattr(message, "tool_calls", []) or []:
                        tool_name = tool_call.get("name", "unknown")
                        tool_args = tool_call.get("args", {})
                        print(f"\n[STEP] Агент вызывает инструмент: {tool_name}")
                        logging.info("TOOL CALL %s args=%s", tool_name, str(tool_args)[:2000])

                    if node_name == "model" and not getattr(message, "tool_calls", []):
                        logging.info("MODEL step completed")
                elif message_type == "tool":
                    print_tool_message(message)

    final_message = _final_ai_message(collected_messages)

    # If a compatible LangGraph version emits no final update, read the final checkpoint.
    if final_message is None:
        try:
            state = agent.get_state(config)
            values = getattr(state, "values", {})
            if isinstance(values, dict):
                final_message = _final_ai_message(values.get("messages", []))
        except Exception:
            logging.exception("Could not read final LangGraph state")

    elapsed = perf_counter() - started_at
    if final_message is not None:
        final_text = message_text(final_message)
        print("\n" + "=" * 68)
        print("AI CODER PRO RESULT")
        print("=" * 68)
        print(final_text or "(финальное сообщение не содержит текста)")
        logging.info("TASK COMPLETED in %.2fs", elapsed)
    else:
        print("\n[ПРЕДУПРЕЖДЕНИЕ] Поток завершился без финального сообщения модели.")
        logging.error("Agent stream ended without a final AI message after %.2fs", elapsed)

    print(f"\n[ВРЕМЯ ВЫПОЛНЕНИЯ: {elapsed:.1f} сек.]")
    return final_message


def read_task() -> str:
    """Read a single-line or explicitly delimited multi-line user request."""
    first_line = input("\nYOU > ").strip()
    if first_line != "/multi":
        return first_line

    print("Вставь текст. Для отправки введи /send отдельной строкой.")
    lines = []
    while True:
        line = input()
        if line.strip() == "/send":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def main():
    print("=" * 68)
    print("                 AI CODER PRO")
    print("=" * 68)
    print("Model:", MODEL)
    print("Ollama:", BASE_URL)
    print("Project root:", PROJECT_ROOT)
    print("Workspace:", WORKSPACE)
    print("Memory: SQLite")
    print("\nКоманды:")
    print("/new    - начать новый диалог")
    print("/multi  - отправить многострочный запрос")
    print("/exit   - выход")
    print("=" * 68)

    db_path = LOG_DIR / "memory.sqlite"
    with SqliteSaver.from_conn_string(str(db_path)) as memory:
        agent = build_agent(memory)
        thread_id = "main"

        while True:
            try:
                task = read_task()
                if not task:
                    continue

                if task.lower() == "/exit":
                    break
                if task.lower() == "/new":
                    thread_id = str(uuid.uuid4())
                    print("Создан новый диалог:", thread_id)
                    continue

                logging.info("USER TASK: %s", task[:2000])
                print("\nAI CODER > Выполняю задачу...\n")
                stream_agent_response(agent, task, thread_id)

            except KeyboardInterrupt:
                print("\nПрервано пользователем.")
                logging.info("User interrupted the current interaction")
            except EOFError:
                print("\nВвод завершён.")
                break
            except Exception as exc:
                logging.exception("AGENT ERROR")
                print("\nОШИБКА:", exc)


if __name__ == "__main__":
    main()
