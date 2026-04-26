"""In-memory job registry. `job.events` is the single source of truth — every SSE
client iterates that list using its own cursor. We do NOT use a queue: doing so
caused every event to be yielded twice to a client that connected after the
events were already in `job.events` (once from the snapshot replay, once from
the queue), producing a visible loop in the streamed reasoning text."""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Job:
    id: str
    variant: dict
    events: list[dict] = field(default_factory=list)
    new_event: asyncio.Event = field(default_factory=asyncio.Event)
    report: dict | None = None
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    error: str | None = None
    chat_history: list[dict] = field(default_factory=list)
    # Audience-mode translations cache. Shape:
    #   translations[mode]["synthesis"] = "..."
    #   translations[mode]["cards"][card_name] = "..."
    # Populated by /api/jobs/{id}/translate; read by the same endpoint to skip
    # re-running Opus when the user toggles back to a previously-visited mode.
    translations: dict[str, dict] = field(default_factory=dict)


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
        # Wake every active stream waiting for new events.
        job.new_event.set()
        job.new_event.clear()
    return emit


async def close_job(job: Job) -> None:
    job.finished_at = time.time()
    job.new_event.set()
    job.new_event.clear()
