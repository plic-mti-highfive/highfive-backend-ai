# Redis Contract - HighFive AI Backend

## Connection

- **Host**: `REDIS_HOST` env var (default: `localhost`)
- **Port**: `REDIS_PORT` env var (default: `6379`)
- **DB**: 0
- **Auth**: None (dev) - implement in production

## Queues (BullMQ)

L'architecture est séparée en deux files distinctes pour isoler les requêtes LLM lentes des opérations mathématiques instantanées.

| Queue Name      | Purpose | Concurrency | Max Retries | Retry Backoff |
|-----------------|---------|-------------|-------------|---------------|
| `ai_tasks`      | Appels API OpenAI (Embeddings, NLP) | 5 | 3 | 1000ms |
| `fast_events`   | Opérations SQL et Mathématiques locales | 2 | 2 | 2000ms |

## Job Schema

### Job Structure

All jobs stored in Redis queues must follow this BullMQ structure:

```json
{
  "name": "job_type_name",
  "data": {
    "tenant_id": "uuid",
    "project_id_or_user_id": "uuid",
    "...": "specific payload"
  }
}
```

### Job States

- `waiting` - Queued, ready to process
- `active` - Currently being processed
- `completed` - Successfully finished
- `failed` - Failed after all retries
- `delayed` - Scheduled for future execution

## Job Types

### update_user_identity

Generates embedding for user identity (bio, skills).

**Queue**: `ai_tasks`
**Job name**: `update_user_identity`  
**Job data**:
```json
{
  "tenant_id": "uuid",
  "user_id": "uuid",
  "payload": {
    "bio": "string",
    "skills": ["string", "string"]
  }
}
```

---

### update_project_identity

Generates embedding for project identity (name, description, tags). Extracts metadata in parallel.

**Queue**: `ai_tasks`
**Job name**: `update_project_identity`  
**Job data**:
```json
{
  "tenant_id": "uuid",
  "project_id": "uuid",
  "payload": {
    "name": "string",
    "description": "string",
    "tags": ["string", "string"],
    "visibility": "string (optional)"
  }
}
```

### user_interacted_with_project

Updates the user's interest vector (Mean Pooling).

**Queue**: `fast_events`
**Job Name**: `user_interacted_with_project`  
**Job data**:

```json
{
  "tenant_id": "uuid",
  "user_id": "uuid",
  "project_id": "uuid",
  "interaction_type": "LIKE" | "APPLY"
}

```

### project_stats_updated

Updates counters for the trending algorithm (Time-Decay).

**Queue**: `fast_events`
**Job Name**: `project_stats_updated`  
**Job data**:

```json
{
  "tenant_id": "uuid",
  "project_id": "uuid",
  "likes": number
}

```

## Monitoring

Queue stats available via health endpoint:

```
GET /api/v1/healthz
```

Response includes:
```json
{
  "workers": {
    "queues": {
      "high_priority": {"waiting": int, "active": int, "failed": int},
      "default": {"waiting": int, "active": int, "failed": int}
    },
    "healthy": bool
  }
}
```

Health is `false` if any queue has `>100 waiting` jobs with `0 active` workers.