import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.responses import success
from app.db.session import get_db
from app.schemas import ChatStreamRequest
from app.services.chat import ChatService
from app.services.places import ConversationService

router = APIRouter(tags=["chat"])


@router.post("/trips/{trip_id}/chat/stream")
async def chat_stream(
    trip_id: str, data: ChatStreamRequest, db: AsyncSession = Depends(get_db)
) -> EventSourceResponse:
    conv_svc = ConversationService(db)
    conv = await conv_svc.get_or_create(trip_id, data.conversation_id)
    await conv_svc.add_user_message(conv.id, trip_id, data.message)
    chat = ChatService(db)

    async def event_generator():
        async for event in chat.stream_answer(trip_id, data.message, conv.id):
            yield {
                "event": event["event"],
                "data": json.dumps(event["data"]),
            }

    return EventSourceResponse(event_generator())


@router.get("/trips/{trip_id}/conversations")
async def list_conversations(trip_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    convs = await ConversationService(db).list_conversations(trip_id)
    return success([c.model_dump() for c in convs])


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(conversation_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    messages = await ConversationService(db).list_messages(conversation_id)
    return success([m.model_dump() for m in messages])
