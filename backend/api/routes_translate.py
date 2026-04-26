"""Translate evidence-packet text into clinician or patient audience modes.

Cached on the Job: re-toggling between modes for the same job after the first
visit to each is a near-zero-cost cache hit (no Opus call at all)."""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.api.jobs import get_job
from backend.reasoning.translate import stream_translate


log = logging.getLogger(__name__)
router = APIRouter()


# Map card_name → JSON-path inside Job.report["evidence"] to use as source text.
# When the path resolves to a dict / list, we json.dumps() it as the source.
# When it resolves to a string, we use it directly.
CARD_SOURCES: dict[str, list[str]] = {
    "aa_substitution": ["annotation", "aa_substitution"],
    "gnomad": ["gnomad"],
    "clinvar": ["clinvar"],
    "uniprot": ["uniprot"],
    "interpro": ["interpro"],
    "alphagenome": ["alphagenome"],
    "structure": ["structure"],
    "sequence_context": ["sequence_context"],
    "conservation": ["conservation"],
    "literature": ["literature"],
    "liver_context": ["liver_context"],
    "disease_spectrum": ["liver_context", "disease_spectrum"],
}


class TranslateRequest(BaseModel):
    target: Literal["synthesis", "card"]
    mode: Literal["clinician", "patient"]
    card: str | None = None


def _walk(d: dict, path: list[str]):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def _evidence_hints(report: dict) -> dict:
    ev = report.get("evidence") or {}
    ann = ev.get("annotation") or {}
    return {
        "variant": ev.get("variant"),
        "gene": ann.get("gene_symbol"),
        "hgvs_c": ann.get("hgvs_c"),
        "hgvs_p": ann.get("hgvs_p"),
        "consequence": ann.get("consequence"),
        "acmg_label": (ev.get("acmg") or {}).get("label"),
        "acmg_posterior": (ev.get("acmg") or {}).get("posterior"),
    }


def _source_text_for(report: dict, target: str, card: str | None) -> str | None:
    if target == "synthesis":
        syn = report.get("synthesis") or {}
        if not any(syn.get(k) for k in ("verdict", "evidence_synthesis", "conflict_resolution",
                                         "evidence_gaps", "clinical_recommendation")):
            return None
        sections = []
        for heading, key in [("## VERDICT", "verdict"),
                             ("## EVIDENCE SYNTHESIS", "evidence_synthesis"),
                             ("## CONFLICT RESOLUTION", "conflict_resolution"),
                             ("## EVIDENCE GAPS", "evidence_gaps"),
                             ("## CLINICAL RECOMMENDATION", "clinical_recommendation")]:
            if syn.get(key):
                sections.append(f"{heading}\n\n{syn[key]}")
        return "\n\n".join(sections)

    if target == "card":
        if not card or card not in CARD_SOURCES:
            return None
        ev = report.get("evidence") or {}
        node = _walk(ev, CARD_SOURCES[card])
        if node is None or (isinstance(node, (dict, list)) and not node):
            return None
        if isinstance(node, str):
            return node
        return json.dumps(node, indent=2, default=str, ensure_ascii=False)

    return None


@router.post("/jobs/{job_id}/translate")
async def translate(job_id: str, req: TranslateRequest) -> EventSourceResponse:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.report is None:
        raise HTTPException(status_code=425, detail="report not ready")

    # Cache lookup
    bucket = job.translations.setdefault(req.mode, {"synthesis": None, "cards": {}})
    cache_key = req.target
    cached = None
    if req.target == "synthesis":
        cached = bucket.get("synthesis")
    elif req.target == "card" and req.card:
        cached = (bucket.get("cards") or {}).get(req.card)

    source_text = _source_text_for(job.report, req.target, req.card)
    if source_text is None:
        raise HTTPException(
            status_code=404,
            detail=f"no source text available for target={req.target}{' card='+req.card if req.card else ''}",
        )

    async def gen() -> AsyncIterator[dict]:
        if cached:
            # Replay the full cached text in one chunk for speed; frontend treats
            # this the same as a streamed response.
            yield {"data": json.dumps({"type": "text_delta", "text": cached, "cached": True})}
            yield {"data": json.dumps({"type": "text_done"})}
            return

        full = []
        try:
            async for delta in stream_translate(
                target=req.target,
                mode=req.mode,
                source_text=source_text,
                card_name=req.card,
                evidence_hints=_evidence_hints(job.report),
            ):
                full.append(delta)
                yield {"data": json.dumps({"type": "text_delta", "text": delta})}
        finally:
            text = "".join(full)
            if text.strip():
                if req.target == "synthesis":
                    bucket["synthesis"] = text
                elif req.target == "card" and req.card:
                    cards = bucket.setdefault("cards", {})
                    cards[req.card] = text
            yield {"data": json.dumps({"type": "text_done"})}

    return EventSourceResponse(gen())
