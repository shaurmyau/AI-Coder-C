from types import SimpleNamespace

from agent import main


def test_message_text_reads_text_blocks():
    message = SimpleNamespace(
        content=[
            {"type": "text", "text": "Сборка "},
            {"type": "text", "text": "завершена"},
        ]
    )

    assert main.message_text(message) == "Сборка завершена"


def test_fallback_answer_uses_short_non_reasoning_summary(monkeypatch):
    observed = {}

    class FakeChatOllama:
        def __init__(self, **kwargs):
            observed.update(kwargs)

        def invoke(self, messages):
            observed["messages"] = messages
            return SimpleNamespace(content="Сборка завершилась ошибкой.")

    monkeypatch.setattr(main, "ChatOllama", FakeChatOllama)
    tool_message = SimpleNamespace(
        type="tool",
        name="build_cpp_project",
        content="EXIT CODE: 1\nerror C2731: WinMain",
    )

    answer = main._fallback_answer("Исправь игру", [tool_message])

    assert answer == "Сборка завершилась ошибкой."
    assert observed["reasoning"] is False
    assert observed["num_predict"] <= 1024
    assert "error C2731" in observed["messages"][1]["content"]


def test_fallback_answer_is_nonempty_if_model_summary_fails(monkeypatch):
    class EmptyChatOllama:
        def __init__(self, **kwargs):
            pass

        def invoke(self, messages):
            return SimpleNamespace(content="")

    monkeypatch.setattr(main, "ChatOllama", EmptyChatOllama)
    tool_message = SimpleNamespace(
        type="tool",
        name="run_tests",
        content="EXIT CODE: 5\nno tests collected",
    )

    answer = main._fallback_answer("Запусти тесты", [tool_message])

    assert answer.strip()
    assert "не сформировал" in answer
    assert "no tests collected" in answer


def test_latest_streamed_text_skips_tool_call_messages():
    streamed = {
        "tool": {"parts": ["вызов инструмента"], "has_tool_calls": True},
        "final": {"parts": ["Итоговый ответ"], "has_tool_calls": False},
    }

    assert main._latest_streamed_text(streamed) == "Итоговый ответ"
