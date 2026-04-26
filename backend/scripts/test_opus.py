"""Smoke test for the Opus 4.7 reasoning layer.

Run from repo root:
  python -m backend.scripts.test_opus

Verifies (a) the model responds, (b) prompt caching writes on the first call,
(c) prompt caching reads on the second call.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Ensure repo root on path when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.config import get_settings  # noqa: E402
from backend.reasoning.prompts import SYSTEM_ACMG  # noqa: E402

import anthropic  # noqa: E402


async def main() -> None:
    s = get_settings()
    if not s.anthropic_api_key:
        print("ANTHROPIC_API_KEY not set; aborting.")
        sys.exit(1)
    client = anthropic.AsyncAnthropic(api_key=s.anthropic_api_key)

    payload_user = [
        {
            "type": "text",
            "text": "# Variant: chr7:87408188 T>C (ABCB4)\n\nReference test packet.",
            "cache_control": {"type": "ephemeral"},
        },
        {"type": "text", "text": "In one short sentence, what gene is affected?"},
    ]

    for label in ("first", "second"):
        async with client.messages.stream(
            model=s.opus_model,
            max_tokens=400,
            thinking={"type": "adaptive", "display": "summarized"},
            output_config={"effort": "low"},
            system=[{"type": "text", "text": SYSTEM_ACMG, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": payload_user}],
        ) as stream:
            text_parts: list[str] = []
            async for event in stream:
                if getattr(event, "type", None) == "content_block_delta":
                    delta = getattr(event, "delta", None)
                    if delta and getattr(delta, "type", None) == "text_delta":
                        text_parts.append(getattr(delta, "text", "") or "")
            final = await stream.get_final_message()
        print(f"--- {label} call ---")
        print("text:", "".join(text_parts).strip()[:200])
        u = final.usage
        print("usage:", json.dumps({
            "input_tokens": getattr(u, "input_tokens", None),
            "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", None),
            "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", None),
            "output_tokens": getattr(u, "output_tokens", None),
        }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
