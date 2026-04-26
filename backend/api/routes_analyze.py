from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, HTTPException
from sse_starlette.sse import EventSourceResponse

from backend.api.jobs import SENTINEL, close_job, create_job, get_job, make_emitter
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
        # Replay anything emitted before the client connected (job started in background_task).
        for ev in list(job.events):
            yield {"data": json.dumps(ev)}

        while True:
            try:
                ev = await asyncio.wait_for(job.queue.get(), timeout=120)
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": "{}"}
                continue
            if ev is SENTINEL or ev.get("type") == "__close__":
                break
            yield {"data": json.dumps(ev)}

    return EventSourceResponse(gen())


@router.get("/jobs/{job_id}/report")
async def report(job_id: str) -> dict:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.report is None:
        raise HTTPException(status_code=425, detail="report not ready")
    return job.report
