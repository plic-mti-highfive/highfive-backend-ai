from src.core.logger import get_logger

logger = get_logger(__name__)


class LLMService:
    async def generate_reply(self, prompt: str, user_id: str) -> str:
        logger.info(f"Generating LLM reply for user {user_id}")
        result = f"Hello user {user_id}, voici une idée pour : {prompt}"
        logger.info("LLM reply generated successfully")
        return result


llm_service = LLMService()
