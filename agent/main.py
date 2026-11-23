"""Interactive entry point for the AI Coder agent."""

import logging
import os
import uuid
from time import perf_counter

from langchain.agents import create_agent
from langchain_core.messages import AIMessage
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
NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "4096"))
REASONING_ENABLED = os.getenv("OLLAMA_REASONING", "false").strip().lower() not in {
    "0", "false", "no", "off",
}

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
        num_predict=NUM_PREDICT,
        reasoning=REASONING_ENABLED,
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
    """Return the latest non-empty assistant answer, never an empty/tool-call message."""
    for message in reversed(messages or []):
        if (
            getattr(message, "type", "") == "ai"
            and not getattr(message, "tool_calls", [])
            and message_text(message).strip()
        ):
            return message
    return None


def _latest_streamed_text(streamed_messages) -> str:
    """Recover the last text response from streamed model chunks."""
    for entry in reversed(list(streamed_messages.values())):
        if entry["has_tool_calls"]:
            continue
        text = "".join(entry["parts"]).strip()
        if text:
            return text
    return ""


def _fallback_answer(task: str, tool_messages) -> str:
    """Try a short non-reasoning summary, then always return a useful status."""
    tool_reports = []
    for message in tool_messages or []:
        if getattr(message, "type", "") != "tool":
            continue
        name = getattr(message, "name", "tool")
        content = message_text(message).strip()
        if content:
            tool_reports.append(f"[{name}]\n{content[-1800:]}")

    evidence = "\n\n".join(tool_reports[-4:]) or "Инструменты не вернули результатов."
    try:
        summarizer = ChatOllama(
            model=MODEL,
            base_url=BASE_URL,
            temperature=0.1,
            num_ctx=min(NUM_CTX, 8192),
            num_predict=min(NUM_PREDICT, 1024),
            reasoning=False,
        )
        response = summarizer.invoke([
            {"role": "system", "content": (
                "Ты формируешь короткий итог работы программного агента. "
                "Отвечай по-русски, только подтверждёнными фактами из результатов "
                "инструментов. Не утверждай, что задача выполнена, если проверка "
                "не прошла. Если данных мало, прямо скажи об этом."
            )},
            {"role": "user", "content": (
                f"Запрос пользователя: {task}\n\nРезультаты инструментов:\n{evidence}"
            )},
        ])
        answer = message_text(response).strip()
        if answer:
            return answer
    except Exception:
        logging.exception("Fallback answer generation failed")

    return (
        "Модель не сформировала итоговый текстовый ответ. Я не буду объявлять задачу "
        "выполненной без подтверждения.\n\n"
        f"Запрос: {task}\n\nПоследние результаты инструментов:\n{evidence}\n\n"
        "Проверь указанные ошибки и повтори запрос после исправления причины."
    )


def stream_agent_response(agent, task: str, thread_id: str):
    """Run the graph, retaining streamed answer text as a fallback to state updates."""
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": MAX_STEPS,
    }
    collected_messages = []
    streamed_messages = {}
    model_activity_announced = False
    model_chunks = 0

    # Remember the checkpoint boundary so a missing new answer cannot reuse an old turn.
    previous_message_count = 0
    try:
        previous_state = agent.get_state(config)
        previous_values = getattr(previous_state, "values", {})
        previous_messages = previous_values.get("messages", []) if isinstance(previous_values, dict) else []
        if isinstance(previous_messages, list):
            previous_message_count = len(previous_messages)
    except Exception:
        logging.debug("No readable checkpoint before this turn", exc_info=True)

    started_at = perf_counter()

    # The v1 tuple format is supported by LangGraph's long-standing stream API.
    for mode, chunk in agent.stream(
        {"messages": [{"role": "user", "content": task}]},
        config=config,
        stream_mode=["messages", "updates"],
    ):
        if mode == "messages":
            message, metadata = chunk
            metadata = metadata if isinstance(metadata, dict) else {}
            if metadata.get("langgraph_node") == "model":
                model_chunks += 1
                if not model_activity_announced:
                    print("[MODEL] Модель начала генерировать ответ.")
                    model_activity_announced = True
                elif model_chunks % 100 == 0:
                    print(f"[MODEL] Получено фрагментов: {model_chunks}", flush=True)

                # Keep only public response content. With reasoning=True, Ollama places
                # private reasoning in additional_kwargs, not in message.content.
                message_id = getattr(message, "id", None)
                stream_run_id = metadata.get("run_id")
                stream_step = metadata.get("langgraph_step", "unknown")
                stream_key = str(message_id or stream_run_id or f"model:{stream_step}")
                entry = streamed_messages.setdefault(
                    stream_key, {"parts": [], "has_tool_calls": False}
                )
                if (
                    getattr(message, "tool_calls", [])
                    or getattr(message, "tool_call_chunks", [])
                ):
                    entry["has_tool_calls"] = True

                text_part = message_text(message)
                if text_part:
                    entry["parts"].append(text_part)
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

    state_messages_for_fallback = []
    if final_message is None:
        try:
            state = agent.get_state(config)
            values = getattr(state, "values", {})
            if isinstance(values, dict):
                state_messages = values.get("messages", [])
                if isinstance(state_messages, list):
                    state_messages_for_fallback = state_messages[previous_message_count:]
                    final_message = _final_ai_message(state_messages_for_fallback)
        except Exception:
            logging.exception("Could not read final LangGraph state")

    # Some integrations emit the final text in messages mode but an empty update message.
    if final_message is None:
        streamed_text = _latest_streamed_text(streamed_messages)
        if streamed_text:
            final_message = AIMessage(content=streamed_text)
            logging.warning(
                "Recovered final assistant text from message stream (%d chunks)",
                model_chunks,
            )

    if final_message is None or not message_text(final_message).strip():
        fallback_messages = collected_messages or state_messages_for_fallback
        final_message = AIMessage(content=_fallback_answer(task, fallback_messages))
        logging.error(
            "Primary model turn had no final text; emitted fallback answer. "
            "chunks=%d elapsed=%.2fs",
            model_chunks,
            perf_counter() - started_at,
        )

    elapsed = perf_counter() - started_at
    final_text = message_text(final_message).strip()
    print("\n" + "=" * 68)
    print("AI CODER PRO RESULT")
    print("=" * 68)
    print(final_text)
    logging.info("TASK TURN FINISHED in %.2fs", elapsed)

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
