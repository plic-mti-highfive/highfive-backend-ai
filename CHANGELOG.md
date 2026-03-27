# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Base de données PostgreSQL**
  - Connexion asynchrone via SQLAlchemy 2.0 + AsyncPG
  - Modèles SQLAlchemy ORM pour embeddings et pgvector
  - Session async avec `AsyncSessionLocal`
- **Migrations de schéma avec Alembic**
  - Migration initiale avec support pgvector
  - Commands alembic `upgrade`, `downgrade`, `history`, `current`
- **Pattern Repository**
  - `embedding_repository.py` pour l'accès aux données
  - Abstraction clean de la logique DB
- **Tests asynchrones**
  - pytest-asyncio pour tests async
  - httpx pour tester les endpoints FastAPI
  - Coverage report avec pytest-cov
  - Configuration pytest dans pyproject.toml
- **Dépendances injectables**
  - `dependencies.py` avec injection de repositories et sessions
- **Health route mise à jour**
  - Endpoint enrichi avec plus d'informations
  - Tests pour health check

### Changed

- Configuration Docker Compose (volumes et version)

### Fixed

- Corrections mineures dans docker-compose.yml

## [1.0.0] - 2026-03-25

### Added

- FastAPI server avec API v1
- Endpoints chat avec LLM service
- Healthcheck endpoint
- JWT authentication
- Middleware de timing pour logs
- Configuration via Pydantic Settings
- Docker et Docker Compose
- Tests avec pytest et coverage
- Linting/formatting avec Ruff
