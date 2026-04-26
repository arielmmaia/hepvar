"""SSE endpoint for the setup-wizard chat."""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.reasoning.setup_chat import stream_setup_chat
from backend.setup.keystore import current_status


log = logging.getLogger(__name__)
router = APIRouter()


class SetupChatMessage(BaseModel):
    role: str
    content: str


class SetupChatRequest(BaseModel):
    history: list[SetupChatMessage] = []
    question: str


@router.post("/setup/chat")
async def setup_chat(req: SetupChatRequest) -> EventSourceResponse:
    """Stream Opus 4.7 setup-wizard responses. Snapshot which providers are
    still missing at the moment of the request and pass them to the prompt;
    the chat will not learn about new keys until the user POSTs to
    /api/setup/keys (which is a separate code path)."""
    status = current_status()
    missing = [p for p, st in status.items() if st != "configured"]
    all_ready = len(missing) == 0

    # Anthropic key must be present to power the chat itself.
    if "anthropic" in missing:
        raise HTTPException(
            status_code=425,
            detail="anthropic key not configured; cannot run setup chat without it",
        )

    async def gen() -> AsyncIterator[dict]:
        full = []
        async for delta in stream_setup_chat(
            history=[m.model_dump() for m in req.history],
            question=req.question,
            missing_providers=missing,
            all_ready=all_ready,
        ):
            full.append(delta)
            yield {"data": json.dumps({"type": "chat_delta", "text": delta})}
        yield {"data": json.dumps({"type": "chat_done"})}

    return EventSourceResponse(gen())
