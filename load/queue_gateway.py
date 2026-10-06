"""Passerelle HTTP minimale vers BullMQ, utilisée par Locust pour publier des jobs.

Locust tourne sous gevent, incompatible avec le client BullMQ (asyncio). Cette passerelle joue le
rôle du core (qui publie les jobs) : `POST /enqueue/{queue}/{name}` avec le payload en JSON.
Sa latence mesurée par Locust = temps de publication Redis + overhead HTTP local.

    uv run uvicorn load.queue_gateway:app --port 8164
"""

from bullmq import Queue
from fastapi import FastAPI, Request

from src.core.config import settings

app = FastAPI()
_queues: dict[str, Queue] = {}


def queue(name: str) -> Queue:
    if name not in _queues:
        _queues[name] = Queue(name, {"connection": settings.redis_opts})
    return _queues[name]


@app.post("/enqueue/{queue_name}/{job_name}")
async def enqueue(queue_name: str, job_name: str, request: Request):
    job = await queue(queue_name).add(job_name, await request.json())
    return {"id": job.id}


@app.get("/stats")
async def stats():
    return {n: await queue(n).getJobCounts("waiting", "active", "completed", "failed") for n in
            ("ai_tasks", "fast_events")}
