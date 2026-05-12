import asyncio
import random
import uuid

from bullmq import Queue
from faker import Faker

from src.core.config import settings

fake = Faker("fr_FR")


async def main():
    print("🚀 Démarrage du simulateur d'événements Core Backend...")

    # On se connecte aux deux queues qu'on a définies dans le dispatcher
    redis_opts = {"host": settings.REDIS_HOST, "port": settings.REDIS_PORT}
    ai_queue = Queue("ai_tasks", {"connection": redis_opts})
    fast_queue = Queue("fast_events", {"connection": redis_opts})

    # On fixe un Tenant ID factice pour le test
    tenant_id = str(uuid.uuid4())

    print("1️⃣ Envoi de 10 Projets à traiter...")
    project_ids = []
    for _ in range(10):
        project_id = str(uuid.uuid4())
        project_ids.append(project_id)

        # Le payload tel que NestJS l'enverrait
        job_data = {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "payload": {
                "name": fake.catch_phrase(),
                "description": fake.text(max_nb_chars=300),
                "visibility": "PUBLIC",
            },
        }
        await ai_queue.add("update_project_identity", job_data)

    print("2️⃣ Envoi de 5 Utilisateurs...")
    user_ids = []
    for _ in range(5):
        user_id = str(uuid.uuid4())
        user_ids.append(user_id)

        job_data = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "payload": {"bio": fake.job(), "skills": [fake.word(), fake.word(), fake.word()]},
        }
        await ai_queue.add("update_user_identity", job_data)

    print("⏳ Pause de 15 secondes pour laisser OpenAI générer les vecteurs...")
    await asyncio.sleep(15)

    print("3️⃣ Simulation de quelques interactions (Likes, Saves)...")
    # On fait liker un projet au hasard par un utilisateur au hasard

    for _ in range(15):
        job_data = {
            "tenant_id": tenant_id,
            "user_id": random.choice(user_ids),
            "project_id": random.choice(project_ids),
            "interaction_type": random.choice(["LIKE", "APPLY"]),
        }
        await fast_queue.add("user_interacted_with_project", job_data)

        # On simule aussi la mise à jour des stats du projet
        stats_data = {
            "tenant_id": tenant_id,
            "project_id": job_data["project_id"],
            "likes": random.randint(1, 50),
        }
        await fast_queue.add("project_stats_updated", stats_data)

    await ai_queue.close()
    await fast_queue.close()
    print("✅ Simulation terminée ! Va regarder les logs de tes workers.")


if __name__ == "__main__":
    asyncio.run(main())
