"""Stream Opus 4.7 ACMG/AMP synthesis with extended (adaptive) thinking + prompt caching.

Notes on Opus 4.7 behaviour (verified at build time):
- Adaptive thinking only — `thinking={"type": "adaptive"}`.
- `display: "summarized"` is required for the model to actually emit thinking content;
  the default `omitted` produces empty thinking blocks.
- No `temperature` / `top_p` / `top_k` — these 400 on 4.7.
- `output_config.effort` controls thinking depth; `xhigh` is recommended for
  intelligence-sensitive coding/agentic work.
- System prompt + evidence block both `cache_control: ephemeral` for ~95% prefix reuse
  across the analysis call and every subsequent chat follow-up.
"""
from __future__ import annotations

import logging
import re
from typing import AsyncIterator

import anthropic

from backend.config import get_settings
from backend.reasoning.prompts import SYSTEM_ACMG, build_evidence_message_blocks
from shared.schemas import EvidencePacket


log = logging.getLogger(__name__)


_SECTION_HEADINGS = [
    ("verdict", "VERDICT"),
    ("evidence_synthesis", "EVIDENCE SYNTHESIS"),
    ("conflict_resolution", "CONFLICT RESOLUTION"),
    ("evidence_gaps", "EVIDENCE GAPS"),
    ("clinical_recommendation", "CLINICAL RECOMMENDATION"),
]


def _detect_section_change(buffer: str) -> tuple[str | None, str]:
    """Look for a `## HEADING` line in the buffer. Return (section_key, leftover_buffer)."""
    for key, heading in _SECTION_HEADINGS:
        m = re.search(rf"##\s*{re.escape(heading)}\s*\n", buffer, flags=re.IGNORECASE)
        if m:
            return key, buffer[m.end():]
    return None, buffer


def _client() -> anthropic.AsyncAnthropic:
    s = get_settings()
    if not s._looks_real(s.anthropic_api_key):
        raise RuntimeError("ANTHROPIC_API_KEY missing or placeholder; set a real key in .env to enable Opus 4.7 synthesis.")
    return anthropic.AsyncAnthropic(api_key=s.anthropic_api_key)


async def stream_synthesis(ev: EvidencePacket) -> AsyncIterator[dict]:
    """Yield reasoning/thinking deltas + parsed sections.

    Yields dicts of shape:
      {"kind": "thinking_delta", "text": "..."}
      {"kind": "reasoning_delta", "text": "..."}
      {"kind": "section", "section": "verdict"|..., "text": "..."}
    """
    s = get_settings()
    client = _client()

    system_blocks = [
        {
            "type": "text",
            "text": SYSTEM_ACMG,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    user_blocks = build_evidence_message_blocks(ev)

    current_section: str | None = None
    section_buffer = ""

    try:
        async with client.messages.stream(
            model=s.opus_model,
            max_tokens=12000,
            thinking={"type": "adaptive", "display": "summarized"},
            # `xhigh` was producing repetitive deliberation on conflicting evidence
            # packets (e.g. mis-attributed PS3 papers); `high` is more decisive while
            # still adequate for ACMG-grade reasoning.
            output_config={"effort": "high"},
            system=system_blocks,
            messages=[{"role": "user", "content": user_blocks}],
        ) as stream:
            async for event in stream:
                etype = getattr(event, "type", None)
                if etype != "content_block_delta":
                    continue
                delta = getattr(event, "delta", None)
                if delta is None:
                    continue
                dtype = getattr(delta, "type", None)

                if dtype == "thinking_delta":
                    text = getattr(delta, "thinking", "") or ""
                    if text:
                        yield {"kind": "thinking_delta", "text": text}

                elif dtype == "text_delta":
                    text = getattr(delta, "text", "") or ""
                    if not text:
                        continue
                    yield {"kind": "reasoning_delta", "text": text}

                    section_buffer += text
                    new_key, leftover = _detect_section_change(section_buffer)
                    if new_key is not None:
                        if current_section is not None:
                            # flush completed previous section
                            prev_text = re.split(rf"##\s*{re.escape([h for k, h in _SECTION_HEADINGS if k == new_key][0])}",
                                                 section_buffer, maxsplit=1, flags=re.IGNORECASE)[0]
                            yield {"kind": "section", "section": current_section, "text": prev_text.strip()}
                        current_section = new_key
                        section_buffer = leftover
            # flush trailing section at stream end
            if current_section is not None and section_buffer.strip():
                yield {"kind": "section", "section": current_section, "text": section_buffer.strip()}

            try:
                final = await stream.get_final_message()
                u = getattr(final, "usage", None)
                if u is not None:
                    log.info(
                        "synthesizer usage: input=%s cache_read=%s cache_create=%s output=%s",
                        getattr(u, "input_tokens", None),
                        getattr(u, "cache_read_input_tokens", None),
                        getattr(u, "cache_creation_input_tokens", None),
                        getattr(u, "output_tokens", None),
                    )
            except Exception:
                pass

    except anthropic.APIStatusError as exc:
        log.exception("opus 4.7 synthesis failed: %s", exc)
        yield {"kind": "reasoning_delta",
               "text": f"\n\n_(Opus 4.7 synthesis unavailable: {exc.status_code} — pipeline evidence is still in the structured report below.)_"}
    except Exception as exc:
        log.exception("opus 4.7 synthesis crashed")
        yield {"kind": "reasoning_delta",
               "text": f"\n\n_(Opus 4.7 synthesis crashed: {type(exc).__name__}: {exc})_"}
