from pydantic import BaseModel, Field


class ChatPromptRequest(BaseModel):
    prompt: str = Field(..., min_length=2, max_length=1000, description="User input for the chat")
    context_id: str | None = Field(default=None, description="The ID of the project or canvas")


class ChatResponse(BaseModel):
    reply: str
    tokens_used: int = 0
