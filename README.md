# HighFive! - AI Backend

FastAPI backend pour les tâches NLP et LLM. Gère le chat avec génération de réponses IA et expose une API REST sécurisée par JWT.

## Prérequis

- Python == 3.11
- uv

## Lancer l'application

### Développement

**Option 1 - Local (recommandé pour le debugging)**

```bash
uv sync
source .venv/bin/activate
python main.py
```

**Option 2 - Docker (hot reload avec isolation)**

```bash
docker compose up --build
```

Les deux approches lancent le serveur avec hot reload sur `http://localhost:8000`. Docs: `http://localhost:8000/docs`

### Production

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Scripts

| Commande          | Description         |
| ----------------- | ------------------- |
| `pytest`          | Lancer les tests    |
| `pytest --cov`    | Tests avec coverage |
| `ruff check src`  | Lint                |
| `ruff format src` | Format              |

## Structure

```
src/
├── server.py              # Création app FastAPI
├── core/                  # Config, middlewares, security
├── api/v1/                # Routes API v1
│   ├── chat.py           # Endpoints chat
│   └── health.py         # Healthcheck
├── schemas/               # Pydantic models
└── services/              # Business logic (LLM, etc)
```

## Architecture

- **FastAPI** pour l'API REST
- **Pydantic** pour la validation des données
- **JWT** pour la sécurité
- **Middleware Timing** pour les logs de perfs
