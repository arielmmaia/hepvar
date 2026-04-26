"""AlphaGenome (Google DeepMind) liver-cell-track predictions.

Uses the official `alphagenome` Python client when installed and the API key is set.
Falls back gracefully (status: missing) so the rest of the pipeline still runs.
"""
from __future__ import annotations

import logging

from backend.cache.store import cached_fetch, variant_key
from backend.config import get_settings
from shared.schemas import AlphaGenomePrediction, VariantInput


log = logging.getLogger(__name__)

LIVER_TRACK_KEYWORDS = ("liver", "hepatocyte", "hepg2", "huh7", "primary hepatocyte")


async def predict_alphagenome(v: VariantInput) -> AlphaGenomePrediction:
    s = get_settings()
    if not s._looks_real(s.alphagenome_api_key):
        return AlphaGenomePrediction(flags=["AlphaGenome API key not configured"])

    vk = variant_key(v.chrom, v.pos, v.ref, v.alt, v.assembly)

    async def fetcher() -> dict:
        try:
            from alphagenome.data import genome  # type: ignore
            from alphagenome.models import dna_client  # type: ignore
        except ImportError:
            return {"error": "alphagenome client not installed; pip install -e .[alphagenome]"}

        try:
            client = dna_client.create(s.alphagenome_api_key)
            chrom = v.chrom if v.chrom.startswith("chr") else f"chr{v.chrom}"
            # AlphaGenome supports window sizes [16384, 131072, 524288, 1048576] only.
            half = 8192
            interval = genome.Interval(chromosome=chrom, start=max(0, v.pos - half), end=v.pos + half)
            variant = genome.Variant(chromosome=chrom, position=v.pos, reference_bases=v.ref, alternate_bases=v.alt)
            outputs = client.predict_variant(
                interval=interval,
                variant=variant,
                ontology_terms=["UBERON:0002107"],  # liver
                requested_outputs=[
                    dna_client.OutputType.RNA_SEQ,
                    dna_client.OutputType.SPLICE_SITES,
                    dna_client.OutputType.ATAC,
                ],
            )

            # Extract reference vs alternate scores per output
            def _max_abs_delta(out_block) -> float | None:
                try:
                    ref = getattr(out_block, "reference", None)
                    alt = getattr(out_block, "alternate", None)
                    if ref is None or alt is None:
                        return None
                    delta = (alt.values - ref.values)
                    return float(abs(delta).max())
                except Exception:
                    return None

            rna = getattr(outputs, "rna_seq", None)
            splice = getattr(outputs, "splice_sites", None)
            atac = getattr(outputs, "atac", None)
            return {
                "rna_log2fc": _max_abs_delta(rna),
                "splice_delta": _max_abs_delta(splice),
                "atac_delta": _max_abs_delta(atac),
                "tracks_used": ["liver"],
            }
        except Exception as exc:
            log.warning("alphagenome call failed: %s", exc)
            return {"error": str(exc)}

    raw = await cached_fetch(variant_key_str=vk, source="alphagenome", fetcher=fetcher, persist_fixture=True)
    if not raw or "error" in raw:
        return AlphaGenomePrediction(flags=[raw.get("error") if raw else "no AlphaGenome response"])

    flags: list[str] = []
    splice = raw.get("splice_delta")
    rna = raw.get("rna_log2fc")
    atac = raw.get("atac_delta")
    if splice is not None and abs(splice) >= 0.2:
        flags.append(f"splicing_disruption_predicted (|Δ|={splice:.2f})")
    if rna is not None and abs(rna) >= 1.0:
        flags.append(f"liver_expression_change_predicted (|log2FC|={rna:.2f})")
    if atac is not None and abs(atac) >= 0.2:
        flags.append(f"chromatin_accessibility_change (|Δ|={atac:.2f})")

    return AlphaGenomePrediction(
        splice_delta=splice,
        expression_log2fc=rna,
        chromatin_accessibility_delta=atac,
        liver_tracks_used=raw.get("tracks_used", []),
        flags=flags,
    )
