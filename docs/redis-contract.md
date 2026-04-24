# Redis Contract - HighFive Backend

## Connection

- **Host**: `REDIS_HOST` env var (default: `localhost`)
- **Port**: `REDIS_PORT` env var (default: `6379`)
- **DB**: 0
- **Auth**: None (dev) - implement in production

## Queues

| Queue Name      | Concurrency | Max Retries | Retry Backoff | Remove on Complete |
|-----------------|-------------|-------------|---------------|--------------------|
| `high_priority` | 5           | 3           | 1000ms        | true               |
| `default`       | 2           | 2           | 2000ms        | true               |

## Job Schema

### Job Structure

All jobs stored in Redis queues follow this structure:

```json
{
  "id": "job-uuid",
  "queueName": "default|high_priority",
  "data": {
    "type": "job_type_name",
    "user_id": "uuid",
    "timestamp": "2026-04-23T14:30:00Z",
    "payload": {}
  },
  "opts": {
    "attempts": 0,
    "delay": 0,
    "removeOnComplete": true,
    "removeOnFail": false
  },
  "attemptsMade": 0,
  "progress": 0,
  "timestamp": 1713880200000
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

**Queue**: `high_priority`  
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

**Queue**: `default`  
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


