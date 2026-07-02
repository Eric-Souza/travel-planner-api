import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from langchain_ollama import ChatOllama, OllamaEmbeddings
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.llm.chains import build_grounded_answer_chain
from app.services.llm.messages import chunk_content, to_langchain_messages
from app.services.llm.mock import MockLLMProvider, mock_embedding
from app.services.llm.provider import ChatResult, StreamEvent

logger = logging.getLogger(__name__)
settings = get_settings()


class LangChainOllamaProvider:
    """Ollama integration via LangChain (ChatOllama + OllamaEmbeddings + LCEL chains)."""

    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.chat_model_name = settings.ollama_chat_model
        self.embedding_model_name = settings.ollama_embedding_model
        self._chat_model: ChatOllama | None = None
        self._embeddings: OllamaEmbeddings | None = None
        self._grounded_chain = None

    def _get_chat_model(self) -> ChatOllama:
        if self._chat_model is None:
            self._chat_model = ChatOllama(
                model=self.chat_model_name,
                base_url=self.base_url,
                temperature=0.2,
            )
        return self._chat_model

    def _get_embeddings(self) -> OllamaEmbeddings:
        if self._embeddings is None:
            self._embeddings = OllamaEmbeddings(
                model=self.embedding_model_name,
                base_url=self.base_url,
            )
        return self._embeddings

    def _get_grounded_chain(self):
        if self._grounded_chain is None:
            self._grounded_chain = build_grounded_answer_chain(self._get_chat_model())
        return self._grounded_chain

    async def _available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def chat(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None
    ) -> ChatResult:
        if not await self._available():
            return await MockLLMProvider().chat(messages, tools)
        chat_model = self._get_chat_model()
        if tools:
            bound = chat_model.bind_tools(tools)
            response = await bound.ainvoke(to_langchain_messages(messages))
        else:
            response = await chat_model.ainvoke(to_langchain_messages(messages))
        tool_calls = []
        if getattr(response, "tool_calls", None):
            tool_calls = list(response.tool_calls)
        return ChatResult(content=chunk_content(response.content), tool_calls=tool_calls)

    async def stream_chat(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None
    ) -> AsyncIterator[StreamEvent]:
        if not await self._available():
            async for event in MockLLMProvider().stream_chat(messages, tools):
                yield event
            return

        chat_model = self._get_chat_model()
        if tools:
            chat_model = chat_model.bind_tools(tools)

        output_chars = 0
        async for chunk in chat_model.astream(to_langchain_messages(messages)):
            text = chunk_content(chunk.content)
            if text:
                output_chars += len(text)
                yield StreamEvent(type="token", data={"text": text})
        yield StreamEvent(type="done", data={"usage": {"output_chars": output_chars}})

    async def structured_output(
        self, messages: list[dict[str, str]], schema: type[BaseModel]
    ) -> BaseModel:
        if not await self._available():
            return await MockLLMProvider().structured_output(messages, schema)

        lc_messages = to_langchain_messages(messages)
        chat_model = self._get_chat_model()
        for method in ("json_schema", "function_calling"):
            try:
                structured = chat_model.with_structured_output(schema, method=method)
                result = await structured.ainvoke(lc_messages)
                if isinstance(result, schema):
                    return result
                return schema.model_validate(result)
            except Exception as exc:
                logger.debug("LangChain structured_output method=%s failed: %s", method, exc)

        schema_json = schema.model_json_schema()
        fallback_messages = messages + [
            {
                "role": "user",
                "content": (
                    "Return ONLY valid JSON matching this schema:\n"
                    f"{json.dumps(schema_json)}"
                ),
            }
        ]
        result = await self.chat(fallback_messages)
        try:
            parsed = json.loads(result.content)
            return schema.model_validate(parsed)
        except Exception:
            logger.warning("LangChain structured output failed, using mock")
            return await MockLLMProvider().structured_output(messages, schema)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not await self._available():
            return await MockLLMProvider().embed(texts)
        try:
            vectors = await self._get_embeddings().aembed_documents(texts)
            return [list(vector) for vector in vectors]
        except Exception as exc:
            logger.warning("LangChain embeddings failed, using mock vectors: %s", exc)
            return [mock_embedding(text) for text in texts]

    async def grounded_answer(self, question: str, sources: str) -> str:
        if not await self._available():
            prompt = f"Question: {question}\n\nSources:\n{sources}"
            result = await MockLLMProvider().chat([{"role": "user", "content": prompt}])
            return result.content.strip()
        chain = self._get_grounded_chain()
        return await chain.ainvoke({"question": question, "sources": sources})
