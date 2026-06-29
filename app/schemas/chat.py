from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import MessageRole
from app.schemas.common import APIModel
from app.schemas.itinerary import SourceCitation


class ChatRequest(APIModel):
    message: str = Field(min_length=1)
    conversation_id: UUID | None = None


class MessageResponse(APIModel):
    id: UUID
    role: MessageRole
    content: str
    sources: list[SourceCitation] | None
    tool_results: list[dict] | None
    status: str
    created_at: datetime


class ConversationResponse(APIModel):
    id: UUID
    trip_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(APIModel):
    conversations: list[ConversationResponse]
    total: int


class MessageListResponse(APIModel):
    messages: list[MessageResponse]
    total: int
