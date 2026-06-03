# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2026-04-24

### Added
- Rajouuté script de seeds
- Nouvelle migration alemenbic pour supporter GIN sur les payloads JSONB
- Support des interactions users (like, join project) dans le matchmaking
- Ajout d'une route de projet trending

### Changed
- Remplacé `TextProcessor` par `NLPManager` avec spaCy pour normalisation et tokenization de texte

### Fixed
- Changmements mineurs du docker-compose
- Plusieur fixes

## [2.0.0] - 2026-04-24

### Added

- **Worker Service avec BullMQ & Redis**
  - Architecture worker distribuée avec support multi-queue (high_priority, default)
  - Implémentation BullMQ pour job processing asynchrone
  - Configuration workers via `config/workers.yaml` avec support concurrency et retries
  - Worker CLI entry point pour démarrage du service
  - Factory pattern pour création dynamique de workers depuis configuration
  - WorkerMonitor pour health checks et statistiques queues
  - Redis Insight intégré dans docker-compose pour monitoring
  - Tests unitaires complets pour factory, dispatcher et monitor

- **Logging System**
  - Logger centralisé via `src/core/logger.py`
  - Format structuré avec timestamps, levels et stack traces

- **Docker Architecture Révisée**
  - Séparation Dockerfile en `Dockerfile.api` (serveur) et `Dockerfile.worker` (worker)
  - Service worker_service dans docker-compose avec volumes et dépendances
  - Support hot reload pour développement local

- **Documentation**
  - Contrat Redis complet : `docs/redis-contract.md`
  - Spécifications job schemas et queue definitions
  - Guide monitoring et troubleshooting

- **Infrastructure & LLM**
  - Base de données PostgreSQL avec SQLAlchemy 2.0 + AsyncPG
  - Support pgvector avec index HNSW
  - Migrations Alembic pour gestion du schéma
  - Pattern Repository pour abstraction des données
  - Protocol `LLMProvider` et implémentation OpenAI
  - Service d'embeddings avec matchmaking utilisateurs-projets
  - TextProcessor pour normalisation de texte

- **API REST**
  - Matchmaking endpoints basé sur embeddings
  - Health check enrichi avec stats workers et queues
  - Chat et LLM endpoints

- **Tests**
  - Structure organisation tests (integration/, unit/)
  - Tests async avec pytest-asyncio
  - Coverage reports
  - Tests worker handlers (integration)
  - Tests worker factory et dispatcher (unit)

### Changed

- Réorganisation structure src/worker avec CLI, factory, dispatcher
- Health endpoint enrichi pour inclure statistiques workers
- Configuration LLM provider pour meilleure extensibilité
- Docker-compose restructuré avec services séparés API et Worker
- GitHub Actions pipeline mis à jour pour build des deux images

### Fixed

- Corrections Docker (layer optimization, ENV variables)
- Mineurs bugs worker initialization

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
