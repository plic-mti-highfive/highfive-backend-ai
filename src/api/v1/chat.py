from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_user
from src.schemas import ChatPromptRequest, ChatResponse
from src.services import llm_service

router = APIRouter(prefix="/chat", tags=["IA Chat"])


@router.post("/generate", response_model=ChatResponse)
async def generate_idea(request: ChatPromptRequest, user: dict = Depends(get_current_user)):
    user_id = user.get("sub", "unknown_user")

    reply = await llm_service.generate_reply(prompt=request.prompt, user_id=user_id)

    return ChatResponse(reply=reply, tokens_used=42)
