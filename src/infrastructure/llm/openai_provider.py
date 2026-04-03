from openai import AsyncOpenAI

import src.core.config as config
from src.infrastructure.llm_provider import ILLMProvider


class OpenAIProvider(ILLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=config.settings.OPENAI_API_KEY)
        self.model = "text-embedding-3-small"

    async def generate_embedding(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty or whitespace.")

        try:
            response = await self.client.embeddings.create(input=text, model=self.model)
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"OpenAI Error: {str(e)}")
