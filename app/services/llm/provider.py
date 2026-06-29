from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel


@dataclass
class ChatResult:
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class StreamEvent:
    type: str
    data: dict[str, Any]


class LLMProvider(Protocol):
    async def chat(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None
    ) -> ChatResult: ...

    async def stream_chat(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None
    ) -> AsyncIterator[StreamEvent]: ...

    async def structured_output(
        self, messages: list[dict[str, str]], schema: type[BaseModel]
    ) -> BaseModel: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...
