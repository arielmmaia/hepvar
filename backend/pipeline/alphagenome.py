"""AlphaGenome (Google DeepMind) liver-cell-track predictions.

Uses the official `alphagenome` Python client when installed and the API key is set.
Falls back gracefully (status: missing) so the rest of the pipeline still runs.

Beyond the scalar `splice_delta` / `rna_log2fc` summaries, we emit a per-modality
breakdown including a position-resolved Δ sparkline (mean across tracks within a
±N bp window centred on the variant) so the dashboard can visualise the signal
shape, not just a single number.
"""
from __future__ import annotations

import logging

from backend.cache.store import cached_fetch, variant_key
from backend.config import get_settings
from shared.schemas import AlphaGenomeModality, AlphaGenomePrediction, AlphaGenomeTrack, VariantInput


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
            import numpy as np

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
                    dna_client.OutputType.SPLICE_SITE_USAGE,
                    dna_client.OutputType.ATAC,
                ],
            )

            # Per-modality summary + sparkline.
            modalities: list[dict] = []
            ref_obj = getattr(outputs, "reference", None)
            alt_obj = getattr(outputs, "alternate", None)
            if ref_obj is None or alt_obj is None:
                return {"error": "alphagenome returned neither reference nor alternate"}

            sparkline_n = 64  # downsampled length around the variant
            for output_name in ("rna_seq", "splice_sites", "splice_site_usage", "atac"):
                ref_track = getattr(ref_obj, output_name, None)
                alt_track = getattr(alt_obj, output_name, None)
                if ref_track is None or alt_track is None:
                    continue
                try:
                    ref_v = np.asarray(ref_track.values)
                    alt_v = np.asarray(alt_track.values)
                except Exception:
                    continue
                if ref_v.shape != alt_v.shape:
                    continue
                delta = alt_v - ref_v  # (positions, tracks)
                abs_delta = np.abs(delta)
                if abs_delta.size == 0:
                    continue
                max_abs = float(abs_delta.max())
                sum_abs = float(abs_delta.sum())

                # Centre on variant: AlphaGenome interval is [interval.start, interval.end);
                # variant index = v.pos - interval.start. Take a ±half_window slice and
                # downsample to `sparkline_n` mean buckets across all tracks.
                pos_idx = max(0, min(ref_v.shape[0] - 1, v.pos - interval.start))
                window = 512  # bp half-window around the variant
                lo = max(0, pos_idx - window)
                hi = min(ref_v.shape[0], pos_idx + window)
                slice_ = delta[lo:hi]
                # Mean over tracks → 1D
                mean_per_pos = slice_.mean(axis=1) if slice_.ndim == 2 else slice_
                # Downsample by averaging into `sparkline_n` buckets
                if mean_per_pos.size > sparkline_n:
                    edges = np.linspace(0, mean_per_pos.size, sparkline_n + 1).astype(int)
                    spark = [float(mean_per_pos[edges[i]:edges[i + 1]].mean()) for i in range(sparkline_n)]
                else:
                    spark = [float(x) for x in mean_per_pos.tolist()]

                # Track-level summaries from metadata
                track_list: list[dict] = []
                meta = getattr(ref_track, "metadata", None)
                n_tracks = ref_v.shape[1] if ref_v.ndim > 1 else 1
                for t_i in range(min(n_tracks, 8)):
                    t_max = float(abs_delta[:, t_i].max()) if abs_delta.ndim == 2 else max_abs
                    t_sum = float(abs_delta[:, t_i].sum()) if abs_delta.ndim == 2 else sum_abs
                    name = None
                    biosample = None
                    if meta is not None and hasattr(meta, "iloc"):
                        try:
                            row = meta.iloc[t_i]
                            for k in ("name", "Assay title", "biosample_name", "biosample_type"):
                                if k in row.index and row[k] is not None:
                                    if name is None:
                                        name = str(row[k])
                                    elif biosample is None:
                                        biosample = str(row[k])
                        except Exception:
                            pass
                    track_list.append({"name": name, "biosample": biosample,
                                        "max_abs_delta": t_max, "sum_abs_delta": t_sum})

                modalities.append({
                    "output_type": output_name,
                    "n_tracks": int(n_tracks),
                    "max_abs_delta": max_abs,
                    "sum_abs_delta": sum_abs,
                    "sparkline": spark,
                    "sparkline_window": window,
                    "tracks": track_list,
                })

            # Backwards-compatible scalar summaries for the original card.
            def _mod_max(name: str) -> float | None:
                for m in modalities:
                    if m["output_type"] == name:
                        return m["max_abs_delta"]
                return None

            return {
                "rna_log2fc": _mod_max("rna_seq"),
                "splice_delta": _mod_max("splice_sites") or _mod_max("splice_site_usage"),
                "atac_delta": _mod_max("atac"),
                "tracks_used": ["liver"],
                "modalities": modalities,
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

    modalities = [AlphaGenomeModality(
        output_type=m["output_type"],
        n_tracks=m.get("n_tracks", 0),
        max_abs_delta=m.get("max_abs_delta"),
        sum_abs_delta=m.get("sum_abs_delta"),
        sparkline=m.get("sparkline", []) or [],
        sparkline_window=m.get("sparkline_window"),
        tracks=[AlphaGenomeTrack(**t) for t in m.get("tracks", [])],
    ) for m in raw.get("modalities", []) or []]

    return AlphaGenomePrediction(
        splice_delta=splice,
        expression_log2fc=rna,
        chromatin_accessibility_delta=atac,
        liver_tracks_used=raw.get("tracks_used", []),
        flags=flags,
        modalities=modalities,
    )
