from typing import Protocol


class ILLMProvider(Protocol):
    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate a mathematical vector from a text.
        """
        ...

    async def extract_metadata(self, text: str) -> dict:
        """Extract themes and sub-themes from a text and return them as a dictionary."""
        ...
