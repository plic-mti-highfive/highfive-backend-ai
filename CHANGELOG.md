# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Base de données**
  - PostgreSQL avec SQLAlchemy 2.0 + AsyncPG
  - Support pgvector avec index HNSW
  - Migrations Alembic pour gestion du schéma
- **Infrastructure LLM et embeddings**
  - Pattern Repository pour abstraction des données
  - Protocol `LLMProvider` et implémentation OpenAI
  - Service d'embeddings avec matchmaking utilisateurs-projets
  - TextProcessor pour normalisation de texte
- **API REST**
  - Matchmaking endpoints basé sur embeddings
  - Health check enrichi
  - Chat et LLM endpoints
- **Tests**
  - Structure organisation tests (integration/, unit/)
  - Tests async avec pytest-asyncio
  - Coverage reports

### Changed

- Réorganisation structure des tests (dossiers integration/ et unit/)
- Améliorations TextProcessor et EmbeddingService
- Configuration LLM provider pour meilleure extensibilité

### Fixed

- Corrections mineures configuration Docker

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
