from collections import OrderedDict
from types import SimpleNamespace

from langchain_core.messages import AIMessage

from agent import main


def test_message_text_extracts_text_blocks_and_ignores_non_text_blocks():
    message = SimpleNamespace(
        content=[
            {"type": "text", "text": "Ответ "},
            {"type": "image", "image_url": "ignored"},
            {"type": "text", "text": "готов"},
        ]
    )

    assert main.message_text(message) == "Ответ готов"


def test_final_ai_message_skips_empty_and_tool_call_messages():
    tool_call = SimpleNamespace(
        type="ai",
        content="",
        tool_calls=[{"name": "read_file", "args": {"path": "main.py"}}],
    )
    empty = SimpleNamespace(type="ai", content="   ", tool_calls=[])
    final = AIMessage(content="Игра собрана.")

    assert main._final_ai_message([final, tool_call, empty]) is final


def test_latest_streamed_text_uses_last_non_tool_response():
    streamed = OrderedDict(
        [
            ("first", {"parts": ["Старый ответ"], "has_tool_calls": False}),
            ("tool", {"parts": [], "has_tool_calls": True}),
            ("last", {"parts": ["Новый ", "ответ."], "has_tool_calls": False}),
        ]
    )

    assert main._latest_streamed_text(streamed) == "Новый ответ."


def test_stream_response_recovers_text_when_update_message_is_empty(capsys):
    empty_update_message = SimpleNamespace(type="ai", content="", tool_calls=[])

    class FakeAgent:
        def get_state(self, _config):
            return SimpleNamespace(values={"messages": []})

        def stream(self, *_args, **_kwargs):
            yield (
                "messages",
                (
                    SimpleNamespace(
                        id="final-message",
                        content="Агент завершил ответ.",
                        tool_calls=[],
                        tool_call_chunks=[],
                    ),
                    {"langgraph_node": "model", "langgraph_step": 1},
                ),
            )
            yield ("updates", {"model": {"messages": [empty_update_message]}})

    result = main.stream_agent_response(FakeAgent(), "тест", "test-thread")

    assert main.message_text(result) == "Агент завершил ответ."
    assert "Агент завершил ответ." in capsys.readouterr().out


def test_build_agent_enables_reasoning_and_sets_output_budget(monkeypatch):
    captured = {}

    def fake_chat_ollama(**kwargs):
        captured["model"] = kwargs
        return "fake-model"

    def fake_create_agent(**kwargs):
        captured["agent"] = kwargs
        return "fake-agent"

    monkeypatch.setattr(main, "ChatOllama", fake_chat_ollama)
    monkeypatch.setattr(main, "create_agent", fake_create_agent)
    monkeypatch.setattr(main, "REASONING_ENABLED", True)
    monkeypatch.setattr(main, "NUM_PREDICT", 8192)

    assert main.build_agent("fake-checkpointer") == "fake-agent"
    assert captured["model"]["reasoning"] is True
    assert captured["model"]["num_predict"] == 8192
    assert captured["agent"]["checkpointer"] == "fake-checkpointer"
