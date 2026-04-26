"""Conversational follow-up endpoint.

Cache strategy: the system prompt and the evidence-packet block are both
`cache_control: ephemeral`, so each subsequent question reuses ~95% of the prior
prefix. Only the trailing `# Hepatologist question` block varies between turns.
"""
from __future__ import annotations

import logging
from typing import AsyncIterator

import anthropic

from backend.config import get_settings
from backend.reasoning.prompts import CHAT_SYSTEM, build_chat_user_blocks


log = logging.getLogger(__name__)


def _client() -> anthropic.AsyncAnthropic:
    s = get_settings()
    if not s._looks_real(s.anthropic_api_key):
        raise RuntimeError("ANTHROPIC_API_KEY missing or placeholder; set a real key in .env.")
    return anthropic.AsyncAnthropic(api_key=s.anthropic_api_key)


async def stream_chat(
    *,
    evidence: dict,
    synthesis: dict | None,
    history: list[dict],
    question: str,
) -> AsyncIterator[str]:
    """Yield text deltas. Caller wraps each into an SSE chat_delta event."""
    s = get_settings()
    client = _client()

    system_blocks = [
        {
            "type": "text",
            "text": CHAT_SYSTEM,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    user_blocks = build_chat_user_blocks(evidence, synthesis, history, question)

    try:
        async with client.messages.stream(
            model=s.opus_model,
            max_tokens=2400,
            thinking={"type": "adaptive", "display": "summarized"},
            output_config={"effort": "high"},
            system=system_blocks,
            messages=[{"role": "user", "content": user_blocks}],
        ) as stream:
            async for event in stream:
                if getattr(event, "type", None) != "content_block_delta":
                    continue
                delta = getattr(event, "delta", None)
                if delta is None:
                    continue
                if getattr(delta, "type", None) == "text_delta":
                    text = getattr(delta, "text", "") or ""
                    if text:
                        yield text

            try:
                final = await stream.get_final_message()
                u = getattr(final, "usage", None)
                if u is not None:
                    log.info(
                        "chat usage: input=%s cache_read=%s cache_create=%s output=%s",
                        getattr(u, "input_tokens", None),
                        getattr(u, "cache_read_input_tokens", None),
                        getattr(u, "cache_creation_input_tokens", None),
                        getattr(u, "output_tokens", None),
                    )
            except Exception:
                pass
    except anthropic.APIStatusError as exc:
        log.exception("opus 4.7 chat failed: %s", exc)
        yield f"\n\n_(Opus 4.7 chat unavailable: {exc.status_code} — try again.)_"
    except Exception as exc:
        log.exception("opus 4.7 chat crashed")
        yield f"\n\n_(Opus 4.7 chat crashed: {type(exc).__name__}: {exc})_"
