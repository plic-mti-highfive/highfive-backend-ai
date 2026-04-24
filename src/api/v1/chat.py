from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_user
from src.core.logger import get_logger
from src.schemas import ChatPromptRequest, ChatResponse
from src.services import llm_service

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["IA Chat"])


@router.post("/generate", response_model=ChatResponse)
async def generate_idea(request: ChatPromptRequest, user: dict = Depends(get_current_user)):
    user_id = user.get("sub", "unknown_user")
    logger.info(f"Chat request from user {user_id}: {request.prompt[:50]}...")

    reply = await llm_service.generate_reply(prompt=request.prompt, user_id=user_id)
    logger.info(f"Chat response generated for user {user_id}")

    return ChatResponse(reply=reply, tokens_used=42)
