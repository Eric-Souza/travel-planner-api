import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.services.llm.messages import chunk_content, to_langchain_messages


def test_to_langchain_messages_maps_roles() -> None:
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
    ]
    converted = to_langchain_messages(messages)
    assert isinstance(converted[0], SystemMessage)
    assert isinstance(converted[1], HumanMessage)
    assert isinstance(converted[2], AIMessage)


def test_chunk_content_handles_string_and_blocks() -> None:
    assert chunk_content("hello") == "hello"
    assert chunk_content([{"type": "text", "text": "world"}]) == "world"


@pytest.mark.asyncio
async def test_invoke_grounded_answer_with_mock_provider() -> None:
    from app.services.llm.chains import invoke_grounded_answer
    from app.services.llm.mock import MockLLMProvider

    answer = await invoke_grounded_answer(
        MockLLMProvider(),
        "What time is check-in?",
        ["[hotel.pdf p.1]: Check-in at 15:00"],
    )
    assert "check-in" in answer.lower() or "[mock]" in answer


def test_get_llm_provider_uses_mock_by_default() -> None:
    from app.services.llm.mock import MockLLMProvider
    from app.services.llm.ollama import get_llm_provider

    provider = get_llm_provider()
    assert isinstance(provider, MockLLMProvider)
