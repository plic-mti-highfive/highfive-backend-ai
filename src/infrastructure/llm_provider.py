from typing import Protocol


class ILLMProvider(Protocol):
    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate a mathematical vector from a text.
        """
        ...
