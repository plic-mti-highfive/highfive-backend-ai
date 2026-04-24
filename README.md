# HighFive! - AI Backend

FastAPI backend pour les tâches NLP et LLM. Gère le chat avec génération de réponses IA et expose une API REST sécurisée par JWT.

## Prérequis

- Python >= 3.11
- uv
- Docker & Docker Compose (pour PostgreSQL, Redis, RedisInsight)

## Configuration

### Fichier .env

Créez un fichier `.env` à la racine du projet (voir `.env.exemple`):

```env
# Server
ENV=dev
JWT_SECRET=your-secret-key-here-change-in-production

# Database
DATABASE_URI=postgresql+asyncpg://admin:admin@localhost:5432/highfive

# LLM Provider
OPENAI_API_KEY=sk-...

# Redis & Workers
REDIS_HOST=localhost
REDIS_PORT=6379
WORKERS_CONFIG_PATH=config/workers.yaml
```

**Variables importantes:**
- `ENV`: `dev` ou `prod` (affecte logs SQL et comportement serveur)
- `JWT_SECRET`: Clé secrète pour les tokens JWT (à générer de façon sécurisée en prod)
- `DATABASE_URI`: URI de connexion PostgreSQL avec asyncpg
- `OPENAI_API_KEY`: Clé API OpenAI pour LLM
- `REDIS_HOST`: Hostname du serveur Redis (défaut: `localhost`)
- `REDIS_PORT`: Port du serveur Redis (défaut: `6379`)
- `WORKERS_CONFIG_PATH`: Chemin vers la configuration des workers (défaut: `config/workers.yaml`)

## Lancer l'application

### Installation des dépendances

```bash
uv sync
source .venv/bin/activate  # Linux/Mac
# ou .venv\Scripts\activate sur Windows
```

### Développement

**Option 1 - Local (recommandé pour le debugging)**

```bash
# Terminal 1 - Démarrer la base de données et Redis
docker compose up db redis redisinsight

# Terminal 2 - Appliquer les migrations
alembic upgrade head

# Terminal 3 - Lancer le serveur
python main.py

# Terminal 4 - Lancer le worker (optionnel pour jobs asynchrones)
python -m src.worker.cli
```

Accès:
- API: `http://localhost:8000`
- Swagger Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Healthcheck: `http://localhost:8000/api/v1/healthz`
- RedisInsight: `http://localhost:5540`

**Option 2 - Docker (hot reload avec isolation)**

```bash
# Tout en un : API, Worker, DB, Redis, RedisInsight
docker compose up --build
```

Les deux approches lancent le serveur avec hot reload (uvicorn en mode dev).

### Production

**API Server:**
```bash
python -m src.main
```

**Worker Service:**
```bash
python -m src.worker.cli
```

## Scripts

### Tests et Qualité

| Commande                      | Description                           |
| ----------------------------- | ------------------------------------- |
| `pytest`                      | Lancer les tests                      |
| `pytest --cov`                | Tests avec coverage report            |
| `pytest tests/unit`           | Tests unitaires uniquement            |
| `pytest tests/integration`    | Tests d'intégration uniquement        |
| `ruff check src`              | Lint                                  |
| `ruff format src`             | Format                                |

### Migrations et Base de données

| Commande                      | Description                           |
| ----------------------------- | ------------------------------------- |
| `alembic revision --autogenerate -m "message"` | Créer une migration auto-générée |
| `alembic upgrade head`        | Appliquer les migrations              |
| `alembic history`             | Voir l'historique des migrations      |
| `alembic current`             | Voir la version actuelle de la BD     |

### Workers

| Commande                      | Description                           |
| ----------------------------- | ------------------------------------- |
| `python -m src.worker.cli`    | Démarrer le worker localement         |
| `docker compose up worker_service` | Démarrer worker en Docker       |

## Structure

```
.
├── config/
│   └── workers.yaml         # Configuration des workers BullMQ
├── docs/
│   └── redis-contract.md    # Spécifications Redis et queues
├── migrations/              # Alembic migrations (schema DB)
│   ├── env.py               # Configuration Alembic
│   └── versions/            # Migration scripts
├── src/
│   ├── server.py            # Création app FastAPI
│   ├── core/                # Config, middlewares, security
│   │   ├── config.py        # Pydantic Settings (variables d'env)
│   │   ├── logger.py        # Logger centralisé
│   │   ├── middlewares.py   # Middlewares FastAPI
│   │   └── security.py      # JWT et auth
│   ├── api/v1/              # Routes API v1
│   │   ├── chat.py          # Endpoints chat
│   │   ├── health.py        # Healthcheck + stats workers
│   │   ├── router.py        # Routeur principal
│   │   └── dependencies.py  # Dépendances injectables
│   ├── infrastructure/       # Couche infrastructure
│   │   ├── database.py      # Connexion PostgreSQL, session async
│   │   ├── llm_provider.py  # Interface LLM provider
│   │   ├── worker_monitor.py # Monitoring des queues Redis
│   │   └── llm/
│   │       └── openai_provider.py  # Implémentation OpenAI
│   ├── models/              # Modèles SQLAlchemy
│   │   └── embedding.py     # Modèles DB (ORM)
│   ├── repositories/        # Data access layer
│   │   └── embedding_repository.py  # Repository pattern
│   ├── schemas/             # Pydantic models (validation/sérialisation)
│   │   ├── chat.py          # Schémas API
│   │   └── embeddings.py    # Schémas embeddings
│   ├── services/            # Business logic
│   │   ├── llm_service.py   # Logique LLM/chat
│   │   ├── embedding_service.py   # Service embeddings
│   │   └── matchmaking_service.py # Service matchmaking
│   └── worker/              # Worker service
│       ├── cli.py           # Entry point worker CLI
│       ├── main.py          # Initialisation worker
│       ├── factory.py       # Factory pour créer workers BullMQ
│       ├── dispatcher.py    # Job dispatcher async
│       └── handlers.py      # Handlers pour types de jobs
├── tests/                   # Tests (unit + integration)
│   ├── conftest.py          # Fixtures pytest
│   ├── unit/                # Tests unitaires
│   └── integration/         # Tests d'intégration
├── Dockerfile.api           # Image Docker API Server
├── Dockerfile.worker        # Image Docker Worker Service
├── docker-compose.yml       # Services (API, Worker, DB, Redis, RedisInsight)
├── alembic.ini              # Configuration migrations
├── pyproject.toml           # Dépendances et config projet
└── main.py                  # Entry point API server
```

## Architecture

### Stack Technique

- **FastAPI** pour l'API REST avec async/await
- **Pydantic** pour la validation des données et settings
- **SQLAlchemy 2.0** + **AsyncPG** pour l'accès async à PostgreSQL
- **pgvector** pour les embeddings vectoriels avec index HNSW
- **BullMQ** + **Redis** pour le traitement asynchrone des jobs
- **Alembic** pour la gestion des migrations de schéma
- **JWT** pour la sécurité (tokens Bearer)
- **Pytest + pytest-asyncio** pour les tests

### Composants

1. **API Server** (`Dockerfile.api`): Serveur FastAPI avec endpoints REST
2. **Worker Service** (`Dockerfile.worker`): Service worker BullMQ pour jobs asynchrones
3. **PostgreSQL**: Base de données avec pgvector pour embeddings
4. **Redis**: Queue manager pour workers (BullMQ)
5. **RedisInsight**: UI de monitoring Redis (développement)

### Gestion de la base de données

**Connexion asynchrone** via SQLAlchemy + AsyncPG:
```python
# src/infrastructure/database.py gère la création du moteur et les sessions
engine = create_async_engine(DATABASE_URI, echo=settings.ENV=="dev")
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
```

**Migrations** avec Alembic:
```bash
# Créer une migration auto-générée
alembic revision --autogenerate -m "Add users table"

# Appliquer les migrations
alembic upgrade head

# Revenir à une version précédente
alembic downgrade -1
```

Le dossier `migrations/versions/` contient tous les scripts de migration versionnés.

## Workers & Job Processing

### Architecture

L'application utilise une architecture **worker distribuée** avec **Redis** et **BullMQ** pour le traitement asynchrone des jobs:

- **API Server**: Reçoit les requêtes et soumet les jobs aux queues Redis
- **Redis Queues**: Stockage des jobs (high_priority, default)
- **Worker Service**: Traite les jobs en arrière-plan de manière asynchrone

```
API Server -> Redis Queues -> Worker Service
```

### Configuration des Workers

Fichier: `config/workers.yaml`

```yaml
workers:
  - name: "high_priority"
    queue: "high_priority"
    concurrency: 5           # Nombre de jobs traités en parallèle
    max_retries: 3           # Nombre de tentatives en cas d'erreur
    retry_backoff_ms: 1000   # Délai avant retry (ms)
    remove_on_complete: true # Supprimer après succès

  - name: "default"
    queue: "default"
    concurrency: 2
    max_retries: 2
    retry_backoff_ms: 2000
    remove_on_complete: true
```

### Démarrer les Workers Localement

```bash
# Option 1 - Directement avec Python
python -m src.worker.cli

# Option 2 - Via Docker Compose (avec API)
docker compose up --build
```

Le worker se connecte automatiquement à Redis et commence à traiter les jobs.

### Monitoring & Health Checks

L'endpoint health inclut les statistiques des queues:

```bash
GET /api/v1/status

Response:
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "workers": {
    "queues": {
      "high_priority": {"waiting": 5, "active": 2, "failed": 0},
      "default": {"waiting": 10, "active": 1, "failed": 0}
    },
    "healthy": true
  }
}
```

### Redis Insight

Interface de monitoring Redis disponible dans docker-compose:

```bash
docker compose up redisinsight
# Accès: http://localhost:5540
```

Permet de visualiser:
- Queues et jobs en temps réel
- État des jobs (waiting, active, completed, failed)
- Statistiques d'exécution

### Documentation Complète

Voir [docs/redis-contract.md](docs/redis-contract.md) pour:
- Spécifications Redis et queue definitions
- Job schemas et contracts
- Best practices et troubleshooting
- Guide d'intégration pour nouveaux job types

## Redis

### Configuration

Redis est lancé automatiquement avec Docker Compose:

```yaml
redis:
  image: redis:latest
  ports:
    - "6379:6379"
```

**Variables d'environnement:**
- `REDIS_HOST`: Hostname du serveur Redis (défaut: `localhost`)
- `REDIS_PORT`: Port du serveur Redis (défaut: `6379`)

### Connexion Locale

```bash
# Accès au CLI Redis
redis-cli

# Commandes utiles
KEYS *                      # Voir toutes les clés
QUEUE high_priority:jobs    # Voir les jobs de la queue
DEL key                     # Supprimer une clé
```


### Pattern Repository

Les repositories (ex: `embedding_repository.py`) encapsulent la logique d'accès aux données:
- Queries réutilisables
- Abstraction de la base de données
- Facilite les tests (mock repositories)
