"""Build a ±N residue strip around the variant with nearby functional annotations
(active sites, binding sites, domain boundaries) — derived from UniProt + InterPro
data already in the evidence packet, no extra API calls."""
from __future__ import annotations

import re
from typing import Any

from shared.schemas import SequenceAnnotation, SequenceContext


WINDOW = 15  # residues either side of the variant


def _interpro_overlap(interpro: dict | None, target: int, low: int, high: int) -> list[SequenceAnnotation]:
    out: list[SequenceAnnotation] = []
    for entry in (interpro or {}).get("entries", []) or []:
        etype = (entry.get("type") or "").lower()
        if etype not in ("domain", "motif", "repeat", "region"):
            continue
        for frag in entry.get("fragments", []) or []:
            s = frag.get("start")
            e = frag.get("end")
            if s is None or e is None:
                continue
            # Mark domain boundary if it falls inside our window
            if low <= s <= high:
                out.append(SequenceAnnotation(
                    position=s, relative=s - target, kind="domain_start",
                    label=f"start of {entry.get('name')}",
                ))
            if low <= e <= high:
                out.append(SequenceAnnotation(
                    position=e, relative=e - target, kind="domain_end",
                    label=f"end of {entry.get('name')}",
                ))
    return out


def _walker_a_motif(sequence: str, low: int, high: int, target: int) -> list[SequenceAnnotation]:
    """Walker A P-loop signature: GXXXXGK[ST] — common in ABC transporters and
    AAA+ ATPases. We search the strip's wider sequence for an obvious match and
    annotate the start position if it lands within the displayed window."""
    out: list[SequenceAnnotation] = []
    if not sequence:
        return out
    pattern = re.compile(r"G.{4}GK[ST]")
    for m in pattern.finditer(sequence):
        # m.start() is 0-indexed within `sequence`. The sequence starts at
        # residue (low) — but we don't know absolute offsets here without the caller.
        out.append(SequenceAnnotation(
            position=low + m.start(), relative=(low + m.start()) - target, kind="motif",
            label=f"Walker A P-loop ({m.group()})",
        ))
    return out


def build_sequence_context(
    accession: str | None,
    sequence: str | None,
    aa_position: int | None,
    aa_ref: str | None,
    aa_alt: str | None,
    uniprot: dict | None,
    interpro: dict | None,
) -> SequenceContext | None:
    if not sequence or not aa_position:
        return None
    n = len(sequence)
    if not (1 <= aa_position <= n):
        return None

    low = max(1, aa_position - WINDOW)
    high = min(n, aa_position + WINDOW)
    strip = sequence[low - 1:high]
    variant_offset = aa_position - low

    annotations: list[SequenceAnnotation] = []

    # Variant marker (the focal residue)
    annotations.append(SequenceAnnotation(
        position=aa_position,
        relative=0,
        kind="variant",
        label=f"variant: {aa_ref or '?'}{aa_position}{aa_alt or '?'}",
    ))

    # UniProt active sites + binding sites within window
    for site in (uniprot or {}).get("active_sites", []) or []:
        pos = site.get("position")
        if pos is None:
            continue
        if low <= pos <= high:
            kind = "active_site"
            desc = (site.get("description") or "").lower()
            if "binding" in desc:
                kind = "binding_site"
            annotations.append(SequenceAnnotation(
                position=pos, relative=pos - aa_position, kind=kind,
                label=site.get("description") or kind,
            ))

    # UniProt domain boundaries within window
    for d in (uniprot or {}).get("domains", []) or []:
        s = d.get("begin")
        e = d.get("end")
        if s is None or e is None:
            continue
        if low <= s <= high:
            annotations.append(SequenceAnnotation(
                position=s, relative=s - aa_position, kind="domain_start",
                label=f"start of {d.get('description', 'domain')}",
            ))
        if low <= e <= high:
            annotations.append(SequenceAnnotation(
                position=e, relative=e - aa_position, kind="domain_end",
                label=f"end of {d.get('description', 'domain')}",
            ))

    # InterPro fragments
    annotations.extend(_interpro_overlap(interpro, aa_position, low, high))

    # Look for Walker A in a slightly wider context (±60 aa) so it gets
    # annotated even if it's just outside the displayed strip — clinicians
    # care about it as a landmark.
    wide_low = max(1, aa_position - 60)
    wide_high = min(n, aa_position + 60)
    wide_seq = sequence[wide_low - 1:wide_high]
    for ann in _walker_a_motif(wide_seq, wide_low, wide_high, aa_position):
        if low <= ann.position <= high:
            annotations.append(ann)

    # Sort by position, dedupe by (position, kind)
    seen: set = set()
    deduped: list[SequenceAnnotation] = []
    for a in sorted(annotations, key=lambda x: (x.position, x.kind)):
        key = (a.position, a.kind, a.label)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(a)

    return SequenceContext(
        accession=accession,
        start=low,
        end=high,
        sequence=strip,
        variant_position=aa_position,
        variant_offset=variant_offset,
        variant_ref=aa_ref,
        variant_alt=aa_alt,
        annotations=deduped,
    )
