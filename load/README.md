# Test de charge (Locust)

Mesure les temps de réponse de l'API IA sous un trafic réaliste. Aucun appel OpenAI : le worker de
charge utilise `scripts/fake_provider.py` (embedding déterministe + latence simulée).

## Scénario (`locustfile.py`)

Un utilisateur Locust = un visiteur (réflexion 0,5-2 s entre actions), JWT signé avec `JWT_SECRET`.

| Poids | Action | Type |
| --- | --- | --- |
| 55 | `GET /matchmaking/users/{id}/projects` (utilisateurs variés, 50 % tirés parmi 5 % d'« utilisateurs chauds ») | lecture |
| 10 | idem avec `?tags=<thème>` | lecture |
| 12 | `GET /matchmaking/trending` | lecture |
| 8 | `GET /matchmaking/projects/{id}/users` | lecture |
| 2 | `GET /livez` | sonde |
| 6 | `user_interacted_with_project` + `project_stats_updated` (file `fast_events`) | écriture |
| 2 | `update_user_identity` (file `ai_tasks`) | écriture |
| 1 | `update_project_identity` (file `ai_tasks`) | écriture |

Les écritures passent par `queue_gateway.py` (petite API qui publie dans BullMQ comme le fait le
core ; Locust/gevent ne peut pas utiliser le client BullMQ asyncio). Leur latence = publication
Redis, pas traitement : le traitement est observable via `GET :8164/stats` (backlog des files).

## Lancer

Prérequis : Postgres pgvector + Redis, `.env` (`JWT_SECRET`, `OPENAI_API_KEY` factice,
`DATABASE_URI`, `REDIS_PORT`), `uv sync`, modèle spaCy installé, `uv run alembic upgrade head`.

```bash
# 1. données (2000 utilisateurs, 500 projets, 40 % d'utilisateurs avec vecteur d'intérêt) ~1 min
uv run python -m load.seed --users 2000 --projects 500

# 2. services (3 terminaux)
uv run uvicorn main:app --port 8163                       # API (--workers N pour tester le scaling)
uv run python -m load.run_worker --latency 0.05           # workers BullMQ, provider factice
uv run uvicorn load.queue_gateway:app --port 8164         # passerelle de publication

# 3. charge
export JWT_SECRET=...   QUEUE_GATEWAY=http://127.0.0.1:8164
uv run locust -f load/locustfile.py --headless -u 100 -r 10 -t 3m --host http://127.0.0.1:8163 \
    --csv load/results            # ou sans --headless : UI sur http://localhost:8089
```

`-u` = utilisateurs simulés, `-r` = montée en charge (utilisateurs/s). Pour isoler les données,
créer une base dédiée (`CREATE DATABASE highfive_load`) et pointer `DATABASE_URI` dessus. Le seed
écrit `load/seed_data.json` (ignoré par git) ; `SEED_FILE` permet d'en choisir un autre.
