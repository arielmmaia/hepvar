from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
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
        # mode="json" turns datetime/Enum into JSON-native types so json.dumps()
        # in the SSE generator doesn't raise. Without this, the `done` event was
        # silently failing and the chat composer never enabled.
        job.report = report.model_dump(mode="json") if hasattr(report, "model_dump") else report
        await emit({"type": "done", "data": job.report})
    except Exception as exc:  # pragma: no cover
        log.exception("pipeline failed")
        job.error = str(exc)
        await emit({"type": "error", "text": str(exc)})
    finally:
        await close_job(job)


@router.get("/jobs/{job_id}/stream")
async def stream(
    job_id: str,
    request: Request,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> EventSourceResponse:
    """SSE endpoint with Last-Event-ID resume support.

    Each event carries `id: <index>` so the browser caches it. If the
    EventSource auto-reconnects (network blip, server idle timeout, etc.),
    the browser sends `Last-Event-ID: <last>` and we resume from
    cursor=<last>+1 instead of replaying from index 0. This is what stops
    the visible "loop" when synthesis is long-running or the connection
    flickers.
    """
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    try:
        start_cursor = int(last_event_id) + 1 if last_event_id is not None else 0
    except ValueError:
        start_cursor = 0

    async def gen() -> AsyncIterator[dict]:
        cursor = start_cursor
        while True:
            if await request.is_disconnected():
                return

            while cursor < len(job.events):
                ev = job.events[cursor]
                yield {"id": str(cursor), "data": json.dumps(ev)}
                cursor += 1

            if job.finished_at is not None and cursor >= len(job.events):
                return

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
