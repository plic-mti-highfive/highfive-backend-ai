# HighFive! - AI Backend

FastAPI backend pour les tâches NLP et LLM. Gère le chat avec génération de réponses IA et expose une API REST sécurisée par JWT.

## Prérequis

- Python >= 3.11
- uv
- Docker & Docker Compose (pour la base de données PostgreSQL)

## Configuration

### Fichier .env

Créez un fichier `.env` à la racine du projet :

```env
ENV=dev
JWT_SECRET=your-secret-key-here-change-in-production
DATABASE_URI=postgresql+asyncpg://admin:admin@localhost:5432/highfive
```

**Variables importantes:**
- `ENV`: `dev` ou `prod` (affecte les logs SQL et le comportement du serveur)
- `JWT_SECRET`: Clé secrète pour les tokens JWT (à générer de façon sécurisée en prod)
- `DATABASE_URI`: URI de connexion PostgreSQL avec asyncpg

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
# Terminal 1 - Démarrer la base de données
docker compose up db

# Terminal 2 - Appliquer les migrations
alembic upgrade head

# Terminal 3 - Lancer le serveur
python main.py
```

Accès:
- API: `http://localhost:8000`
- Swagger Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Healthcheck: `http://localhost:8000/api/v1/healthz`

**Option 2 - Docker (hot reload avec isolation)**

```bash
docker compose up --build
```

Les deux approches lancent le serveur avec hot reload (uvicorn en mode dev).

### Production

```bash
uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 4
```

## Scripts

| Commande                      | Description                           |
| ----------------------------- | ------------------------------------- |
| `pytest`                      | Lancer les tests                      |
| `pytest --cov`                | Tests avec coverage report            |
| `ruff check src`              | Lint                                  |
| `ruff format src`             | Format                                |
| `alembic revision --autogenerate -m "message"` | Créer une migration auto-générée |
| `alembic upgrade head`        | Appliquer les migrations              |
| `alembic history`             | Voir l'historique des migrations      |
| `alembic current`             | Voir la version actuelle de la BD     |

## Structure

```
.
├── migrations/                # Alembic migrations (schema DB)
│   ├── env.py               # Configuration Alembic
│   └── versions/            # Migration scripts
├── src/
│   ├── server.py            # Création app FastAPI
│   ├── core/                # Config, middlewares, security
│   │   ├── config.py        # Pydantic Settings (variables d'env)
│   │   ├── middlewares.py   # Middlewares FastAPI
│   │   └── security.py      # JWT et auth
│   ├── api/v1/              # Routes API v1
│   │   ├── chat.py          # Endpoints chat
│   │   ├── health.py        # Healthcheck
│   │   ├── router.py        # Routeur principal
│   │   └── dependencies.py  # Dépendances injectables
│   ├── infrastructure/       # Couche infrastructure
│   │   └── database.py      # Connexion PostgreSQL, session async
│   ├── models/              # Modèles SQLAlchemy
│   │   └── embedding.py     # Modèles DB (ORM)
│   ├── repositories/        # Data access layer
│   │   └── embedding_repository.py  # Repository pattern
│   ├── schemas/             # Pydantic models (validation/sérialisation)
│   │   └── chat.py          # Schémas API
│   └── services/            # Business logic
│       └── llm_service.py   # Logique LLM/chat
├── tests/                   # Tests unitaires
├── alembic.ini              # Configuration migrations
└── pyproject.toml           # Dépendances et config projet
```

## Architecture

- **FastAPI** pour l'API REST
- **Pydantic** pour la validation des données et settings
- **SQLAlchemy 2.0** + **AsyncPG** pour l'accès async à PostgreSQL
- **pgvector** pour les embeddings vectoriels
- **Alembic** pour la gestion des migrations de schéma
- **JWT** pour la sécurité (tokens Bearer)
- **Middleware Timing** pour les logs de perfs

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

### Pattern Repository

Les repositories (ex: `embedding_repository.py`) encapsulent la logique d'accès aux données:
- Queries réutilisables
- Abstraction de la base de données
- Facilite les tests (mock repositories)
