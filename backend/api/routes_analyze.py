from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, HTTPException
from sse_starlette.sse import EventSourceResponse

from backend.api.jobs import close_job, create_job, get_job, make_emitter
from backend.pipeline.orchestrator import run_pipeline
from shared.schemas import VariantInput


log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze")
async def analyze(variant: VariantInput, background_tasks: BackgroundTasks) -> dict:
    job = create_job(variant.model_dump())
    background_tasks.add_task(_run_job, job.id, variant)
    return {"jobId": job.id}


async def _run_job(job_id: str, variant: VariantInput) -> None:
    job = get_job(job_id)
    if job is None:
        return
    emit = make_emitter(job)
    try:
        report = await run_pipeline(variant, emit)
        report.job_id = job_id
        job.report = report.model_dump() if hasattr(report, "model_dump") else report
        await emit({"type": "done", "data": job.report})
    except Exception as exc:  # pragma: no cover
        log.exception("pipeline failed")
        job.error = str(exc)
        await emit({"type": "error", "text": str(exc)})
    finally:
        await close_job(job)


@router.get("/jobs/{job_id}/stream")
async def stream(job_id: str) -> EventSourceResponse:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    async def gen() -> AsyncIterator[dict]:
        """`job.events` is authoritative; each connection has its own cursor.
        No queue → no duplicate delivery. New events wake us via job.new_event."""
        cursor = 0
        while True:
            # Drain any events past our cursor.
            while cursor < len(job.events):
                ev = job.events[cursor]
                cursor += 1
                yield {"data": json.dumps(ev)}

            # Job already finished and we've delivered everything → stop.
            if job.finished_at is not None and cursor >= len(job.events):
                return

            # Wait for new event signal, with a periodic ping to keep the
            # connection alive in proxies that idle-close.
            try:
                await asyncio.wait_for(job.new_event.wait(), timeout=15.0)
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": "{}"}

    return EventSourceResponse(gen())


@router.get("/jobs/{job_id}/report")
async def report(job_id: str) -> dict:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.report is None:
        raise HTTPException(status_code=425, detail="report not ready")
    return job.report
