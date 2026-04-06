import json

from openai import AsyncOpenAI

import src.core.config as config
from src.infrastructure.llm_provider import ILLMProvider


class OpenAIProvider(ILLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=config.settings.OPENAI_API_KEY)
        self.embedding_model = "text-embedding-3-small"
        self.chat_model = "gpt-4o-mini"

    async def generate_embedding(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty or whitespace.")

        try:
            response = await self.client.embeddings.create(input=text, model=self.embedding_model)
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"OpenAI Error: {str(e)}")

    async def extract_metadata(self, text: str) -> dict:
        if not text:
            return {"theme": "Général", "sub_themes": []}

        prompt = """
        Analyse le texte suivant et extrais les catégories.
        Réponds UNIQUEMENT avec un objet JSON valide contenant :
        - "theme": Le thème global principal (ex: "Jeux Vidéo", "Art", "Informatique", "Musique").
        - "sub_themes": Une liste de 2 à 3 sous-catégories ultra-précises (ex: ["Platformer 2D", "Peinture à l'huile"]).
        
        Texte à analyser :
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "Tu es un classificateur de données expert."},
                    {"role": "user", "content": f"{prompt}\n{text}"},
                ],
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {"theme": "Général", "sub_themes": []}
