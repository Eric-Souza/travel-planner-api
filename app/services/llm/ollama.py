from app.core.config import get_settings
from app.services.llm.langchain_provider import LangChainOllamaProvider
from app.services.llm.mock import MockLLMProvider
from app.services.llm.provider import LLMProvider

settings = get_settings()


def get_llm_provider() -> LLMProvider:
    if settings.use_mock_llm:
        return MockLLMProvider()
    return LangChainOllamaProvider()
