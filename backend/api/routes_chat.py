from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.api.jobs import get_job
from backend.reasoning.chat import stream_chat


router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    jobId: str
    history: list[ChatMessage] = []
    question: str


@router.post("/chat")
async def chat(req: ChatRequest) -> EventSourceResponse:
    job = get_job(req.jobId)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.report is None:
        raise HTTPException(status_code=425, detail="report not ready")

    job.chat_history.append({"role": "user", "content": req.question})

    async def gen() -> AsyncIterator[dict]:
        full = []
        async for delta in stream_chat(
            evidence=job.report.get("evidence", {}),
            synthesis=job.report.get("synthesis"),
            history=[m.model_dump() for m in req.history],
            question=req.question,
        ):
            full.append(delta)
            yield {"data": json.dumps({"type": "chat_delta", "text": delta})}
        job.chat_history.append({"role": "assistant", "content": "".join(full)})
        yield {"data": json.dumps({"type": "chat_done"})}

    return EventSourceResponse(gen())
