#!/usr/bin/env bash
# Lance la suite pytest sur des bases JETABLES (pgvector + Redis dans Docker, tmpfs).
# Usage : scripts/test.sh [arguments pytest...]   ex. scripts/test.sh tests/unit -q
# Si DATABASE_URI est déjà défini (CI), aucun conteneur n'est démarré.
set -euo pipefail

cd "$(dirname "$0")/.."

SUFFIX="$(head -c 6 /dev/urandom | od -An -tx1 | tr -d ' \n')"
PG_NAME="hf-ai-test-pg-${SUFFIX}"
REDIS_NAME="hf-ai-test-redis-${SUFFIX}"
STARTED=()
CHILD=""

cleanup() {
  local code=$?
  trap - EXIT INT TERM
  [ -n "$CHILD" ] && kill "$CHILD" 2>/dev/null || true
  for name in "${STARTED[@]:-}"; do
    [ -n "$name" ] && docker rm -f "$name" >/dev/null 2>&1 || true
  done
  exit "$code"
}
trap cleanup EXIT INT TERM

wait_for() { # <description> <commande...>
  local what=$1; shift
  for _ in $(seq 1 60); do
    if "$@" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  echo "Timeout : $what n'est pas prêt." >&2
  return 1
}

host_port() { docker port "$1" "$2" | head -n1 | sed 's/.*://'; }

export ENV="${ENV:-dev}"
export ENVIRONMENT="${ENVIRONMENT:-testing}"
export JWT_SECRET="${JWT_SECRET:-secret-de-test}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-dummy}"

if [ -z "${DATABASE_URI:-}" ]; then
  command -v docker >/dev/null || { echo "docker est requis (ou fournir DATABASE_URI)." >&2; exit 1; }
  STARTED+=("$PG_NAME")
  docker run -d --rm --name "$PG_NAME" \
    --tmpfs /var/lib/postgresql/data \
    -e POSTGRES_USER=admin -e POSTGRES_PASSWORD=admin -e POSTGRES_DB=highfive_test \
    -p 127.0.0.1::5432 pgvector/pgvector:pg16 >/dev/null
  PG_PORT="$(host_port "$PG_NAME" 5432/tcp)"
  wait_for "PostgreSQL" docker exec "$PG_NAME" pg_isready -U admin -d highfive_test
  # pg_isready répond avant la fin de l'init : on valide avec une vraie requête
  wait_for "PostgreSQL (requête)" docker exec "$PG_NAME" psql -U admin -d highfive_test -c 'select 1'
  export DATABASE_URI="postgresql+asyncpg://admin:admin@127.0.0.1:${PG_PORT}/highfive_test"
  if [ -z "${REDIS_HOST:-}" ]; then
    STARTED+=("$REDIS_NAME")
    docker run -d --rm --name "$REDIS_NAME" -p 127.0.0.1::6379 redis:7-alpine >/dev/null
    wait_for "Redis" docker exec "$REDIS_NAME" redis-cli ping
    export REDIS_HOST=127.0.0.1
    export REDIS_PORT="$(host_port "$REDIS_NAME" 6379/tcp)"
  fi
else
  echo "DATABASE_URI fourni : pas de conteneur démarré." >&2
fi

# Commandes lancées en arrière-plan + wait : le trap s'exécute immédiatement sur SIGINT/SIGTERM
# (sinon bash attendrait la fin de pytest) et le processus enfant est tué avant le nettoyage.
uv run alembic upgrade head & CHILD=$!
wait "$CHILD"
uv run pytest "$@" & CHILD=$!
wait "$CHILD"
