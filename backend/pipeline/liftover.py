"""GRCh38 ↔ GRCh37 liftover + the 'wrong-assembly' warning.

The trap the prototype scientific reports flagged: if a clinician copies
a GRCh38 coordinate into a tool that treats it as hg19 (or vice-versa),
the same chromosome:position number can fall in a completely different
gene. We compute both the proper liftover and the gene that overlaps
the input number when (mis-)interpreted under the other assembly, and
warn when they differ.
"""
from __future__ import annotations

import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from backend.cache.store import cached_fetch, variant_key
from shared.schemas import LiftoverInfo, VariantInput


log = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(2), wait=wait_exponential_jitter(initial=1, max=4))
async def _ensembl_map(chrom: str, pos: int, source: str, target: str) -> dict | None:
    chrom = chrom.lstrip("chr")
    url = f"https://rest.ensembl.org/map/human/{source}/{chrom}:{pos}-{pos}/{target}"
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(url, headers={"Accept": "application/json"})
        if r.status_code != 200:
            return None
        return r.json()


@retry(stop=stop_after_attempt(2), wait=wait_exponential_jitter(initial=1, max=4))
async def _ensembl_gene_overlap(chrom: str, pos: int, assembly: str) -> str | None:
    chrom = chrom.lstrip("chr")
    if assembly == "GRCh38":
        url = f"https://rest.ensembl.org/overlap/region/human/{chrom}:{pos}-{pos}?feature=gene"
    else:
        url = f"https://rest.ensembl.org/overlap/region/human/{chrom}:{pos}-{pos}?feature=gene;coord_system_version={assembly}"
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(url, headers={"Accept": "application/json"})
        if r.status_code != 200:
            return None
        data = r.json() or []
        for entry in data:
            if entry.get("biotype") == "protein_coding":
                return entry.get("external_name")
        if data:
            return data[0].get("external_name")
    return None


async def liftover_and_warn(variant: VariantInput, gene_symbol: str | None) -> LiftoverInfo:
    """Returns LiftoverInfo with both the proper cross-assembly mapping AND the
    gene that overlaps the input position if mis-interpreted under the other
    assembly. The warning fires when the two genes disagree."""
    vk = variant_key(variant.chrom, variant.pos, variant.ref, variant.alt, variant.assembly)
    source = variant.assembly
    target = "GRCh37" if source == "GRCh38" else "GRCh38"

    async def fetcher() -> dict:
        # Proper liftover.
        mapped = await _ensembl_map(variant.chrom, variant.pos, source, target)
        mapping = (mapped or {}).get("mappings") or []
        target_pos = None
        target_chrom = None
        if mapping:
            m = mapping[0].get("mapped") or {}
            target_pos = m.get("start")
            target_chrom = m.get("seq_region_name")

        # Gene overlap if the user's number is *misinterpreted* as the other assembly.
        wrong_assembly_gene = None
        try:
            wrong_assembly_gene = await _ensembl_gene_overlap(variant.chrom, variant.pos, target)
        except Exception:
            pass
        return {
            "target_assembly": target,
            "target_pos": target_pos,
            "target_chrom": target_chrom,
            "wrong_assembly_gene": wrong_assembly_gene,
        }

    raw = await cached_fetch(variant_key_str=vk, source="liftover", fetcher=fetcher, persist_fixture=True)
    if not raw:
        return LiftoverInfo(target_assembly=target)

    same_gene = (
        gene_symbol is not None
        and raw.get("wrong_assembly_gene") is not None
        and gene_symbol.upper() == (raw.get("wrong_assembly_gene") or "").upper()
    )
    return LiftoverInfo(
        source_assembly=source,
        source_pos=variant.pos,
        target_assembly=raw.get("target_assembly") or target,
        target_pos=raw.get("target_pos"),
        target_chrom=raw.get("target_chrom"),
        wrong_assembly_gene=raw.get("wrong_assembly_gene"),
        ambiguity_warning=(not same_gene) if (gene_symbol and raw.get("wrong_assembly_gene")) else False,
    )
