"""
Test de charge HighFive IA (Locust).

Scénario réaliste (un « utilisateur » Locust = un visiteur de l'appli) :
  - ~85 % de lectures : reco de projets pour un utilisateur tiré au hasard (avec/sans filtre
    de thème), trending, reco d'utilisateurs pour un projet ;
  - ~15 % d'écritures passées par la file BullMQ (comme le fait le core) : interaction
    LIKE/APPLY + mise à jour des compteurs, mise à jour de bio (identité), mise à jour d'un projet.
  - sondes `/livez` en arrière-plan.

Prérequis : base seedée (`python -m load.seed`), API, worker de charge et passerelle lancés,
voir `load/README.md`. Variables : JWT_SECRET (même secret que l'API), QUEUE_GATEWAY (défaut
http://127.0.0.1:8164), SEED_FILE.
"""

import json
import os
import random
import time
import uuid
from pathlib import Path

import jwt
from locust import HttpUser, between, task

SEED_FILE = Path(os.environ.get("SEED_FILE", Path(__file__).with_name("seed_data.json")))
SEED = json.loads(SEED_FILE.read_text())
TENANT = SEED["tenant_id"]
USERS = SEED["user_ids"]
PROJECTS = SEED["project_ids"]
THEMES = ["WEB", "DATA", "SECURITY", "GAMING"]
GATEWAY = os.environ.get("QUEUE_GATEWAY", "http://127.0.0.1:8164")
JWT_SECRET = os.environ["JWT_SECRET"]

# Quelques utilisateurs « chauds » (consultent souvent leur feed) : loi de Pareto
HOT_USERS = USERS[: max(1, len(USERS) // 20)]

BIOS = [
    "Étudiant passionné de web react et api javascript",
    "Data scientist python machine learning et analyse de données",
    "Spécialiste sécurité réseau pentest et audit",
    "Développeur de jeux unity et gameplay",
]


def make_token(user_id: str) -> str:
    return jwt.encode(
        {"sub": user_id, "tenantId": TENANT, "exp": int(time.time()) + 6 * 3600},
        JWT_SECRET,
        algorithm="HS256",
    )


class VisitorUser(HttpUser):
    wait_time = between(0.5, 2.0)  # temps de réflexion d'un visiteur

    def on_start(self):
        # Le core appelle l'IA avec un jeton de service ; un seul jeton par utilisateur Locust.
        self.token = make_token(str(uuid.uuid4()))
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.me = random.choice(USERS)

    def pick_user(self) -> str:
        return random.choice(HOT_USERS) if random.random() < 0.5 else random.choice(USERS)

    # ----- lectures (85 %) -----
    @task(55)
    def recommendations_for_user(self):
        self.client.get(
            f"/api/v1/matchmaking/users/{self.pick_user()}/projects?limit=10",
            headers=self.headers,
            name="GET /matchmaking/users/{id}/projects",
        )

    @task(10)
    def recommendations_filtered(self):
        self.client.get(
            f"/api/v1/matchmaking/users/{self.pick_user()}/projects"
            f"?limit=10&tags={random.choice(THEMES)}",
            headers=self.headers,
            name="GET /matchmaking/users/{id}/projects?tags",
        )

    @task(12)
    def trending(self):
        self.client.get(
            "/api/v1/matchmaking/trending?limit=10", headers=self.headers, name="GET /matchmaking/trending"
        )

    @task(8)
    def users_for_project(self):
        self.client.get(
            f"/api/v1/matchmaking/projects/{random.choice(PROJECTS)}/users?limit=10",
            headers=self.headers,
            name="GET /matchmaking/projects/{id}/users",
        )

    @task(2)
    def probe(self):
        self.client.get("/api/v1/livez", name="GET /livez")

    # ----- écritures via la file (15 %) -----
    def enqueue(self, queue: str, job: str, data: dict):
        self.client.post(f"{GATEWAY}/enqueue/{queue}/{job}", json=data, name=f"QUEUE {queue}:{job}")

    @task(6)
    def like_or_apply(self):
        project = random.choice(PROJECTS)
        self.enqueue(
            "fast_events",
            "user_interacted_with_project",
            {
                "tenant_id": TENANT,
                "user_id": self.me,
                "project_id": project,
                "interaction_type": random.choice(["LIKE", "LIKE", "APPLY"]),
            },
        )
        self.enqueue(
            "fast_events",
            "project_stats_updated",
            {"tenant_id": TENANT, "project_id": project, "likes": random.randint(1, 200)},
        )

    @task(2)
    def update_bio(self):
        self.enqueue(
            "ai_tasks",
            "update_user_identity",
            {
                "tenant_id": TENANT,
                "user_id": self.me,
                "payload": {
                    "bio": random.choice(BIOS) + f" ({random.randint(0, 10**6)})",
                    "skills": random.sample(["python", "react", "docker", "sql", "unity"], 3),
                },
            },
        )

    @task(1)
    def update_project(self):
        self.enqueue(
            "ai_tasks",
            "update_project_identity",
            {
                "tenant_id": TENANT,
                "project_id": random.choice(PROJECTS),
                "payload": {
                    "name": "Projet mis à jour",
                    "description": random.choice(BIOS) + f" ({random.randint(0, 10**6)})",
                    "tags": ["demo"],
                    "visibility": "PUBLIC",
                },
            },
        )
