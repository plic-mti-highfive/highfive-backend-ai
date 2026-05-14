import asyncio
import uuid

from bullmq import Queue

from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


async def simulate_nestjs():
    redis_opts = settings.redis_opts

    project_queue = Queue("ai_tasks", {"connection": redis_opts})

    tenant_id = "f9f64379-2cf3-447f-bc6d-3c185b1c39ac"
    user_id = "6382a590-726a-4e7a-9e82-6e52a760e094"

    project_id_1 = str(uuid.uuid4())
    project_id_2 = str(uuid.uuid4())

    await project_queue.add(
        "update_project_identity",
        {
            "tenant_id": tenant_id,
            "project_id": project_id_1,
            "payload": {
                "name": "HighFive BullMQ Test",
                "description": "Validation de l'architecture asynchrone modulaire.",
                "tags": ["NestJS", "Python", "Redis"],
            },
        },
    )
    logger.info("Added info project to queue")

    await project_queue.add(
        "update_project_identity",
        {
            "tenant_id": tenant_id,
            "project_id": project_id_2,
            "payload": {
                "name": "HighFive Artistic Project",
                "description": "Un projet artisque sans compétences techniques spécifiques, juste pour tester les recommandations.",
                "tags": ["Art", "Design", "Créativité"],
            },
        },
    )
    logger.info("Added artistic project to queue")

    user_queue = Queue("ai_tasks", {"connection": redis_opts})

    await user_queue.add(
        "update_user_identity",
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "payload": {
                "name": "Alice Smith",
                "bio": "Développeuse passionnée par les systèmes distribués et l'asynchrone.",
                "skills": ["Python", "BullMQ", "Redis"],
            },
        },
    )
    logger.info("Added user identity to queue")

    await project_queue.close()
    await user_queue.close()


if __name__ == "__main__":
    asyncio.run(simulate_nestjs())
