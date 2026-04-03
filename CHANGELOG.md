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
  - Migration vecteurs avec index HNSW, purpose et métadonnées
  - Commands alembic `upgrade`, `downgrade`, `history`, `current`
- **Pattern Repository**
  - `embedding_repository.py` pour l'accès aux données
  - Abstraction clean de la logique DB
- **Infrastructure LLM**
  - `LLMProvider` protocol pour abstraction des fournisseurs d'IA
  - `OpenAIProvider` pour génération d'embeddings via OpenAI
- **Traitement de texte**
  - `TextProcessor` pour normalisation HTML et construction de texte sémantique
  - Support pour construction de profils utilisateur et contenu projet/ticket
- **Service d'embeddings**
  - `EmbeddingService` pour génération et recherche sémantique
  - Matchmaking d'utilisateurs-projets basé sur embeddings
- **Schemas d'embeddings**
  - DTOs pour requêtes/réponses d'embeddings
- **Tests asynchrones**
  - pytest-asyncio pour tests async
  - httpx pour tester les endpoints FastAPI
  - Coverage report avec pytest-cov
  - Configuration pytest dans pyproject.toml
  - Tests pour EmbeddingService et EmbeddingRepository
- **Dépendances injectables**
  - `dependencies.py` avec injection de repositories et sessions
- **Health route mise à jour**
  - Endpoint enrichi avec plus d'informations
  - Tests pour health check

### Changed

- Configuration Docker Compose (volumes et version)
- Modèle Embedding étendu avec champs purpose et metadata
- Repository pattern amélioré avec support pgvector

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
