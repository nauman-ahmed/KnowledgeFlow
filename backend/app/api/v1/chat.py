from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.schemas.chat import ChatRequest
from app.services.chat_service import chat_stream

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def send_message(
    body: ChatRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    return StreamingResponse(
        chat_stream(db, user_id, body.message.strip(), body.conversation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
