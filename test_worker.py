import asyncio
import uuid

from bullmq import Queue

from src.core.config import settings


async def simulate_nestjs():
    redis_opts = settings.redis_opts

    project_queue = Queue("default", {"connection": redis_opts})

    tenant_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())

    await project_queue.add(
        "update_project_identity",
        {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "payload": {
                "name": "HighFive BullMQ Test",
                "description": "Validation de l'architecture asynchrone modulaire.",
                "tags": ["NestJS", "Python", "Redis"],
            },
        },
    )

    user_queue = Queue("high_priority", {"connection": redis_opts})

    user_id = str(uuid.uuid4())

    await user_queue.add(
        "update_user_identity",
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "payload": {
                "name": "Alice Smith",
                "bio": "Développeuse passionnée par les systèmes distribués et l'IA.",
                "skills": ["Python", "Machine Learning", "Docker"],
            },
        },
    )

    await project_queue.close()
    await user_queue.close()


if __name__ == "__main__":
    asyncio.run(simulate_nestjs())
