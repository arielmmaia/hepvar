"""Streaming setup-wizard chat. Calls Opus 4.7 with the SETUP_WIZARD_SYSTEM
prompt + a short system message listing which providers are still missing.

The chat NEVER touches the actual key values. The frontend posts keys to
/api/setup/keys directly. The chat just guides the user through obtaining
each one and (after all are validated) collects the audience mode + variant.
"""
from __future__ import annotations

import logging
from typing import AsyncIterator

import anthropic

from backend.config import get_settings
from backend.reasoning.prompts import SETUP_WIZARD_SYSTEM


log = logging.getLogger(__name__)


def _client() -> anthropic.AsyncAnthropic:
    s = get_settings()
    if not s._looks_real(s.anthropic_api_key):
        raise RuntimeError(
            "ANTHROPIC_API_KEY missing or placeholder; the setup chat needs at "
            "least the Anthropic key to function. Save the Anthropic key first "
            "via the form on the right."
        )
    return anthropic.AsyncAnthropic(api_key=s.anthropic_api_key)


def _status_message(missing: list[str], all_ready: bool) -> str:
    if all_ready:
        return (
            "STATUS UPDATE: all_ready=true. All three keys are configured. "
            "Move on to picking the audience mode and the variant to analyse."
        )
    listed = ", ".join(missing) if missing else "none"
    return (
        f"STATUS UPDATE: providers still missing or not yet validated: {listed}. "
        f"Walk the user through obtaining each one, in the order they want."
    )


async def stream_setup_chat(
    history: list[dict],
    question: str,
    missing_providers: list[str],
    all_ready: bool,
) -> AsyncIterator[str]:
    """Streams text deltas. Caller wraps each into an SSE chat_delta event."""
    s = get_settings()
    client = _client()

    system_blocks = [
        {"type": "text", "text": SETUP_WIZARD_SYSTEM, "cache_control": {"type": "ephemeral"}},
    ]
    user_blocks: list[dict] = []
    if history:
        history_md = "\n\n".join(
            f"**{m.get('role', 'user').title()}:** {m.get('content', '')}" for m in history
        )
        user_blocks.append({"type": "text", "text": f"# Conversation so far\n\n{history_md}"})
    user_blocks.append({"type": "text", "text": _status_message(missing_providers, all_ready)})
    user_blocks.append({"type": "text", "text": f"# User\n\n{question}"})

    try:
        async with client.messages.stream(
            model=s.opus_model,
            max_tokens=2400,
            thinking={"type": "adaptive", "display": "summarized"},
            output_config={"effort": "medium"},
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
                        "setup_chat usage: input=%s cache_read=%s cache_create=%s output=%s",
                        getattr(u, "input_tokens", None),
                        getattr(u, "cache_read_input_tokens", None),
                        getattr(u, "cache_creation_input_tokens", None),
                        getattr(u, "output_tokens", None),
                    )
            except Exception:
                pass
    except anthropic.APIStatusError as exc:
        log.exception("setup chat failed: %s", exc)
        yield f"\n\n_(Setup assistant unavailable: {exc.status_code}. Check your Anthropic key.)_"
    except Exception as exc:
        log.exception("setup chat crashed")
        yield f"\n\n_(Setup assistant crashed: {type(exc).__name__}: {exc})_"
