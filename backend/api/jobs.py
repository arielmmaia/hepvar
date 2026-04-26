"""In-memory job registry. One asyncio.Queue per job for SSE event streaming."""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


SENTINEL = {"type": "__close__"}


@dataclass
class Job:
    id: str
    variant: dict
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=2048))
    events: list[dict] = field(default_factory=list)  # replay buffer
    report: dict | None = None
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    error: str | None = None
    chat_history: list[dict] = field(default_factory=list)


_jobs: dict[str, Job] = {}


def create_job(variant: dict) -> Job:
    job_id = uuid.uuid4().hex[:12]
    job = Job(id=job_id, variant=variant)
    _jobs[job_id] = job
    return job


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def make_emitter(job: Job):
    async def emit(event: dict[str, Any]) -> None:
        job.events.append(event)
        await job.queue.put(event)
    return emit


async def close_job(job: Job) -> None:
    job.finished_at = time.time()
    await job.queue.put(SENTINEL)
