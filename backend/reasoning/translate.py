"""Re-phrase synthesis prose or per-card narratives for clinician/patient audiences.

The original technical text is the ground-truth content; this module only changes
tone and vocabulary. We emit a short summary card narrative when the target is
'card', and the full re-framed prose when the target is 'synthesis'.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Literal

import anthropic

from backend.config import get_settings
from backend.reasoning.prompts import (
    TRANSLATE_SYSTEM_CLINICIAN,
    TRANSLATE_SYSTEM_PATIENT,
)


log = logging.getLogger(__name__)

Mode = Literal["clinician", "patient"]
Target = Literal["synthesis", "card"]


def _client() -> anthropic.AsyncAnthropic:
    s = get_settings()
    if not s._looks_real(s.anthropic_api_key):
        raise RuntimeError("ANTHROPIC_API_KEY missing or placeholder.")
    return anthropic.AsyncAnthropic(api_key=s.anthropic_api_key)


def _system_prompt(mode: Mode) -> str:
    if mode == "patient":
        return TRANSLATE_SYSTEM_PATIENT
    return TRANSLATE_SYSTEM_CLINICIAN


def _user_message(target: Target, mode: Mode, source_text: str, card_name: str | None,
                  evidence_hints: dict | None) -> list[dict]:
    """Build the user-message blocks. The source text is what gets re-framed.
    `evidence_hints` is a small dict of variant-level facts (gene, AA change,
    HGVS) so the model has context without re-reading the whole evidence packet.
    """
    blocks: list[dict] = []
    if evidence_hints:
        blocks.append({
            "type": "text",
            "text": f"# Variant context (do not re-state this verbatim — use it for grounding)\n\n```json\n{json.dumps(evidence_hints, indent=2, default=str)}\n```",
        })
    if target == "synthesis":
        prompt = (
            f"# Source text — re-frame for **{mode}** audience\n\n"
            "Re-write the text below for the target audience while preserving every fact, "
            "number, and citation. Keep the section headings.\n\n"
            "----- BEGIN SOURCE -----\n"
            f"{source_text}\n"
            "----- END SOURCE -----"
        )
    else:
        prompt = (
            f"# Card narrative — generate a single short paragraph (1–4 sentences) for **{mode}** audience\n\n"
            f"Card: **{card_name or 'evidence'}**\n\n"
            "The frontend already shows the underlying numbers, tables, or charts. Your job is "
            "to write a short narrative paragraph — no headings, no bullet lists — that explains "
            "what this card *means* for the audience. Do NOT enumerate the data; interpret it.\n\n"
            "----- BEGIN SOURCE -----\n"
            f"{source_text}\n"
            "----- END SOURCE -----"
        )
    blocks.append({"type": "text", "text": prompt})
    return blocks


async def stream_translate(
    *,
    target: Target,
    mode: Mode,
    source_text: str,
    card_name: str | None = None,
    evidence_hints: dict | None = None,
) -> AsyncIterator[str]:
    """Stream Markdown text deltas. Caller wraps each into an SSE event."""
    s = get_settings()
    client = _client()

    system_blocks = [
        {"type": "text", "text": _system_prompt(mode), "cache_control": {"type": "ephemeral"}},
    ]
    user_blocks = _user_message(target, mode, source_text, card_name, evidence_hints)

    try:
        async with client.messages.stream(
            model=s.opus_model,
            max_tokens=2400 if target == "synthesis" else 600,
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
                        "translate(%s/%s) usage: input=%s cache_read=%s cache_create=%s output=%s",
                        target, mode,
                        getattr(u, "input_tokens", None),
                        getattr(u, "cache_read_input_tokens", None),
                        getattr(u, "cache_creation_input_tokens", None),
                        getattr(u, "output_tokens", None),
                    )
            except Exception:
                pass
    except anthropic.APIStatusError as exc:
        log.exception("translate failed: %s", exc)
        yield f"\n\n_(Translation unavailable: {exc.status_code}.)_"
    except Exception as exc:
        log.exception("translate crashed")
        yield f"\n\n_(Translation crashed: {type(exc).__name__}: {exc})_"
