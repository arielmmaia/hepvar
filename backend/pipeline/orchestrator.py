"""Pipeline orchestrator: drives all sources in parallel, applies ACMG, hands off to Opus 4.7."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable, Callable

from backend.pipeline.acmg import classify
from backend.pipeline.alphagenome import predict_alphagenome
from backend.pipeline.annotate import annotate_variant
from backend.pipeline.databases import fetch_clinvar, fetch_gnomad, fetch_interpro, fetch_lovd, fetch_uniprot
from backend.pipeline.liftover import liftover_and_warn
from backend.pipeline.literature import search_literature
from backend.pipeline.liver_context import fetch_liver_context
from backend.pipeline.sequence_context import build_sequence_context
from backend.pipeline.structure import analyse_structure
from backend.reasoning.synthesizer import stream_synthesis
from shared.schemas import (
    EvidencePacket,
    Report,
    SourceResult,
    SynthesisSection,
    VariantInput,
    VEPAnnotation,
)


log = logging.getLogger(__name__)
Emitter = Callable[[dict], Awaitable[None]]


def _payload_is_substantive(data) -> bool:
    """A payload is 'ok' only if it carries real information beyond an error/flag stub."""
    if data is None:
        return False
    if isinstance(data, dict):
        return bool(data)
    if isinstance(data, list):
        return len(data) > 0
    if hasattr(data, "model_dump"):
        d = data.model_dump(exclude_none=True)
        # AlphaGenome / others sometimes return just a flags array — treat that as 'missing'
        meaningful = {k: v for k, v in d.items() if k not in ("flags", "liver_tracks_used", "matched_aliases")}
        if meaningful:
            return True
        # Has only flags (e.g. AlphaGenome key missing) → mark missing
        return False
    return True


async def _timed(name: str, coro, emit: Emitter, packet_setter):
    """Run a coroutine, time it, emit step events, and route the result via packet_setter."""
    started = time.time()
    await emit({"type": "step", "name": name, "status": "running"})
    try:
        data = await coro
        elapsed = int((time.time() - started) * 1000)
        ok = _payload_is_substantive(data)
        status = "ok" if ok else "missing"
        confidence = "high" if ok else "missing"
        packet_setter(data)
        result = SourceResult(name=name, status=status, confidence=confidence, elapsed_ms=elapsed)
        await emit({
            "type": "step",
            "name": name,
            "status": status,
            "data": _summarise_for_event(name, data),
            "elapsed_ms": elapsed,
        })
        return result
    except Exception as exc:
        elapsed = int((time.time() - started) * 1000)
        log.warning("step %s failed: %s", name, exc)
        await emit({"type": "step", "name": name, "status": "error", "error": str(exc), "elapsed_ms": elapsed})
        return SourceResult(name=name, status="error", error=str(exc), elapsed_ms=elapsed)


def _summarise_for_event(name: str, data) -> dict:
    """Compact event payload for the SSE stream — full data is in the final report.

    Uses mode='json' on Pydantic dumps so datetime/Enum/etc. become JSON-native
    types and json.dumps() in the SSE generator doesn't raise.
    """
    if data is None:
        return {}
    if hasattr(data, "model_dump"):
        return data.model_dump(mode="json")
    if isinstance(data, list):
        return {"count": len(data), "items": [d.model_dump(mode="json") if hasattr(d, "model_dump") else d for d in data[:10]]}
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            if isinstance(v, str) and len(v) > 800:
                out[k] = v[:800] + "…"
            else:
                out[k] = v
        return out
    return {"value": str(data)[:500]}


async def run_pipeline(variant: VariantInput, emit: Emitter) -> Report:
    """Drive the full HepVar pipeline. Returns a structured Report."""
    ev = EvidencePacket(variant=variant)
    sources: list[SourceResult] = []

    await emit({"type": "step", "name": "pipeline", "status": "running",
                "data": {"message": "HepVar pipeline started for "
                          f"{variant.chrom}:{variant.pos} {variant.ref}>{variant.alt} ({variant.assembly})"}})

    # --- Step 1: VEP annotation (gates everything) ---
    def _set_ann(d): ev.annotation = d if isinstance(d, VEPAnnotation) else None
    sources.append(await _timed("annotate", annotate_variant(variant), emit, _set_ann))

    ann = ev.annotation
    gene = ann.gene_symbol if ann else None
    accession = ann.uniprot_accession if ann else None
    hgvs_p = ann.hgvs_p if ann else None
    aa = ann.aa_change if ann else None

    # --- Liftover (also warns on wrong-assembly gene mismatch) ---
    sources.append(await _timed(
        "liftover",
        liftover_and_warn(variant, gene),
        emit,
        lambda d: setattr(ev, "liftover", d),
    ))

    # --- Liver context first (needed to inform structure-step domain hints) ---
    sources.append(await _timed(
        "liver_context",
        fetch_liver_context(variant, gene),
        emit,
        lambda d: setattr(ev, "liver_context", d),
    ))

    # --- Parallel: gnomAD, ClinVar, UniProt, InterPro, LOVD, Literature, AlphaGenome ---
    async def _set_uniprot(d):
        ev.uniprot = d
    async def _set_interpro(d):
        ev.interpro = d
    async def _set_lovd(d):
        ev.lovd = d

    parallel_tasks = [
        _timed("gnomad", fetch_gnomad(variant), emit, lambda d: setattr(ev, "gnomad", d)),
        _timed("clinvar", fetch_clinvar(variant, gene, hgvs_p), emit, lambda d: setattr(ev, "clinvar", d)),
        _timed("uniprot", fetch_uniprot(variant, accession), emit, lambda d: setattr(ev, "uniprot", d)),
        _timed("interpro", fetch_interpro(variant, accession), emit, lambda d: setattr(ev, "interpro", d)),
        _timed("lovd", fetch_lovd(variant, gene), emit, lambda d: setattr(ev, "lovd", d)),
        _timed("literature", search_literature(variant, ann), emit, lambda d: setattr(ev, "literature", d or [])),
        _timed("alphagenome", predict_alphagenome(variant), emit, lambda d: setattr(ev, "alphagenome", d)),
    ]
    sources.extend(await asyncio.gather(*parallel_tasks))

    # --- Step: structure (depends on UniProt sequence + InterPro domain mapping) ---
    sequence = (ev.uniprot or {}).get("sequence")
    aa_position = aa.get("position") if aa else None
    aa_alt_one_letter = aa.get("alt1letter") if aa else None
    domain_at_position = None
    in_active_site = False
    if ev.interpro and aa_position:
        for entry in ev.interpro.get("entries", []):
            for frag in entry.get("fragments", []):
                if frag.get("start") and frag.get("end") and frag["start"] <= aa_position <= frag["end"]:
                    if entry.get("type", "").lower() == "domain" and not domain_at_position:
                        domain_at_position = entry.get("name")
    if ev.uniprot and aa_position:
        for site in ev.uniprot.get("active_sites", []):
            if site.get("position") == aa_position:
                in_active_site = True
                break

    sources.append(await _timed(
        "structure",
        analyse_structure(variant, accession, sequence, aa_position, aa_alt_one_letter, domain_at_position, in_active_site),
        emit,
        lambda d: setattr(ev, "structure", d),
    ))

    # Build the local sequence-context strip (no API calls — derived from
    # already-fetched UniProt + InterPro). Cheap, synchronous-on-data.
    aa_ref_one_letter = aa.get("ref1letter") if aa else None
    seqctx = build_sequence_context(
        accession=accession,
        sequence=sequence,
        aa_position=aa_position,
        aa_ref=aa_ref_one_letter,
        aa_alt=aa_alt_one_letter,
        uniprot=ev.uniprot,
        interpro=ev.interpro,
    )
    if seqctx is not None:
        ev.sequence_context = seqctx
        await emit({
            "type": "step",
            "name": "sequence_context",
            "status": "ok",
            "data": seqctx.model_dump(mode="json"),
        })

    # --- ACMG classification ---
    await emit({"type": "step", "name": "acmg", "status": "running"})
    acmg = classify(ev)
    ev.acmg = acmg
    await emit({
        "type": "step",
        "name": "acmg",
        "status": "ok",
        "data": acmg.model_dump(),
    })
    sources.append(SourceResult(name="acmg", status="ok", confidence="high"))

    ev.sources = sources

    # --- Opus 4.7 synthesis (streams its own deltas) ---
    synthesis = SynthesisSection()
    raw_md_parts: list[str] = []
    thinking_parts: list[str] = []
    try:
        await emit({"type": "step", "name": "synthesis", "status": "running"})
        async for chunk in stream_synthesis(ev):
            kind = chunk.get("kind")
            text = chunk.get("text") or ""
            if kind == "thinking_delta":
                thinking_parts.append(text)
                await emit({"type": "thinking_delta", "text": text})
            elif kind == "reasoning_delta":
                raw_md_parts.append(text)
                await emit({"type": "reasoning_delta", "text": text})
            elif kind == "section":
                section = chunk.get("section")
                content = chunk.get("text", "")
                if hasattr(synthesis, section or ""):
                    setattr(synthesis, section, content)
                await emit({"type": "synthesis_section", "section": section, "text": content})
        await emit({"type": "step", "name": "synthesis", "status": "ok"})
    except Exception as exc:  # pragma: no cover
        log.exception("synthesis failed")
        await emit({"type": "step", "name": "synthesis", "status": "error", "error": str(exc)})

    raw_md = "".join(raw_md_parts) or None
    thinking_log = "".join(thinking_parts) or None

    # If the model produced markdown but didn't emit structured sections, parse them out
    if raw_md and not any([synthesis.verdict, synthesis.evidence_synthesis, synthesis.conflict_resolution,
                            synthesis.evidence_gaps, synthesis.clinical_recommendation]):
        synthesis = _parse_sections(raw_md)

    return Report(
        job_id="",  # filled by route handler if needed
        variant=variant,
        evidence=ev,
        synthesis=synthesis,
        raw_synthesis_markdown=raw_md,
        thinking_log=thinking_log,
    )


def _parse_sections(md: str) -> SynthesisSection:
    """Coarse heading-based parse (fallback when the model emits prose without delimiters)."""
    headings = [
        ("verdict", ["VERDICT"]),
        ("evidence_synthesis", ["EVIDENCE SYNTHESIS", "SYNTHESIS"]),
        ("conflict_resolution", ["CONFLICT RESOLUTION", "CONFLICTS"]),
        ("evidence_gaps", ["EVIDENCE GAPS", "META-COGNITION", "GAPS"]),
        ("clinical_recommendation", ["CLINICAL RECOMMENDATION", "RECOMMENDATION", "NEXT STEPS"]),
    ]
    out = SynthesisSection()
    lines = md.splitlines()
    current = None
    buf: dict[str, list[str]] = {k: [] for k, _ in headings}

    def detect(line: str) -> str | None:
        u = line.strip().lstrip("#*- ").upper().rstrip(":")
        for key, keys in headings:
            for k in keys:
                if u.startswith(k):
                    return key
        return None

    for line in lines:
        h = detect(line)
        if h:
            current = h
            continue
        if current:
            buf[current].append(line)
    for k, _ in headings:
        text = "\n".join(buf[k]).strip()
        if text:
            setattr(out, k, text)
    return out
