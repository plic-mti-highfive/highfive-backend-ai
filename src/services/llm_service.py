class LLMService:
    async def generate_reply(self, prompt: str, user_id: str) -> str:

        return f"Hello user {user_id}, voici une idée pour : {prompt}"


llm_service = LLMService()
