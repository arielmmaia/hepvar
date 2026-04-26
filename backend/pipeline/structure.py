"""Structural analysis: AlphaFold reference, ESMFold variant, AlphaMissense, simple ΔΔG proxy.

The variant fold uses ESMFold via the public ESM Atlas inference endpoint
(`api.esmatlas.com/foldSequence/v1/pdb/`), which accepts a raw amino-acid sequence
and returns a PDB. This avoids waiting on the AlphaFold Server batch queue.
"""
from __future__ import annotations

import asyncio
import logging
from io import StringIO

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from backend.cache.store import cached_fetch, variant_key
from shared.schemas import StructuralAnalysis, VariantInput


log = logging.getLogger(__name__)

AF_API = "https://alphafold.ebi.ac.uk/api/prediction/{acc}"
ALPHAMISS_API = "https://alphafold.ebi.ac.uk/files/AF-{acc}-F1-aa-substitutions.csv"
ESM_ATLAS_FOLD = "https://api.esmatlas.com/foldSequence/v1/pdb/"


def af_pdb_url(accession: str, version: int = 6) -> str:
    return f"https://alphafold.ebi.ac.uk/files/AF-{accession}-F1-model_v{version}.pdb"


@retry(stop=stop_after_attempt(2), wait=wait_exponential_jitter(initial=1, max=4))
async def _af_meta(accession: str) -> dict:
    """Fetches the AF-EBI prediction metadata; returns the first model entry (or {})."""
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(AF_API.format(acc=accession))
        r.raise_for_status()
        data = r.json()
        return data[0] if isinstance(data, list) and data else {}


@retry(stop=stop_after_attempt(2), wait=wait_exponential_jitter(initial=1, max=6))
async def _af_pdb_via_meta(accession: str) -> tuple[str, str]:
    """Returns (pdb_text, pdb_url) using the latest version reported by the API."""
    meta = await _af_meta(accession)
    url = meta.get("pdbUrl") or af_pdb_url(accession, meta.get("latestVersion") or 6)
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.text, url


@retry(stop=stop_after_attempt(2), wait=wait_exponential_jitter(initial=1, max=8))
async def _esmfold(seq: str) -> str:
    """Public ESMFold endpoint. Sequences > ~400 aa are slow; we truncate around the variant."""
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(ESM_ATLAS_FOLD, content=seq.encode(), headers={"Content-Type": "text/plain"})
        r.raise_for_status()
        return r.text


@retry(stop=stop_after_attempt(2), wait=wait_exponential_jitter(initial=1, max=4))
async def _alphamissense_lookup(accession: str, position: int, alt: str) -> dict | None:
    """Fetch AlphaMissense substitution table; find the row for (position, alt).

    AF-EBI substitution CSV format: `protein_variant,am_pathogenicity,am_class`
    where `protein_variant` is `<RefAA><Pos><AltAA>` (one-letter, e.g. `Y1043C`).
    Class is one of: LBen, Amb, LPath.
    """
    url = ALPHAMISS_API.format(acc=accession)
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(url)
            if r.status_code != 200:
                return None
            text = r.text
    except Exception:
        return None
    suffix = f"{position}{alt}"  # e.g. "1043C" — match any ref AA
    for line in text.splitlines():
        head = line.split(",", 1)[0]  # e.g. "Y1043C"
        if len(head) >= 3 and head[0].isalpha() and head.endswith(suffix):
            parts = line.strip().split(",")
            if len(parts) >= 3:
                try:
                    score = float(parts[1])
                except ValueError:
                    continue
                cls = parts[2].strip()
                return {"score": score, "class": cls}
    return None


def _mean_plddt_from_pdb(pdb_text: str) -> float | None:
    vals: list[float] = []
    seen_residues: set[tuple[str, int]] = set()
    for line in pdb_text.splitlines():
        if not line.startswith("ATOM"):
            continue
        if line[12:16].strip() != "CA":
            continue
        chain = line[21]
        try:
            resnum = int(line[22:26])
            b = float(line[60:66])
        except ValueError:
            continue
        key = (chain, resnum)
        if key in seen_residues:
            continue
        seen_residues.add(key)
        vals.append(b)
    if not vals:
        return None
    return round(sum(vals) / len(vals), 1)


def _crude_ddg_from_alphamissense(am_score: float | None) -> float | None:
    """Until a free ΔΔG service is wired, derive a coarse kcal/mol proxy from AlphaMissense.
    Calibrated heuristic: AM ~ 0.0 → ΔΔG ≈ 0; AM ~ 1.0 → ΔΔG ≈ +4 kcal/mol (destabilising).
    Used only as one input among many; flagged to Opus 4.7 as 'derived'.
    """
    if am_score is None:
        return None
    return round(am_score * 4.0, 2)


def _excise_around_variant(seq: str, pos: int, window: int = 200) -> tuple[str, int]:
    """Excise a `window`-residue chunk centered on `pos` (1-indexed) for ESMFold to avoid timeouts.
    Returns (excised_sequence, new_position_within_excerpt).
    """
    if len(seq) <= window:
        return seq, pos
    start = max(1, pos - window // 2)
    end = min(len(seq), start + window)
    start = max(1, end - window)
    return seq[start - 1:end], pos - start + 1


async def analyse_structure(
    v: VariantInput,
    accession: str | None,
    sequence: str | None,
    aa_position: int | None,
    aa_alt_one_letter: str | None,
    domain_at_position: str | None,
    in_active_site: bool,
) -> StructuralAnalysis:
    if not accession:
        return StructuralAnalysis(domain_at_position=domain_at_position, in_active_site=in_active_site)

    vk = variant_key(v.chrom, v.pos, v.ref, v.alt, v.assembly)

    async def fetcher_ref() -> dict:
        try:
            pdb, url = await _af_pdb_via_meta(accession)
            mean_plddt = _mean_plddt_from_pdb(pdb)
            return {"pdb": pdb, "url": url, "mean_plddt": mean_plddt}
        except Exception as exc:
            log.warning("alphafold ref fetch failed: %s", exc)
            return {}

    ref = await cached_fetch(variant_key_str=vk, source="af_ref", fetcher=fetcher_ref, persist_fixture=True)

    am_data = None
    if aa_position and aa_alt_one_letter:
        am_data = await cached_fetch(
            variant_key_str=vk,
            source="alphamissense",
            fetcher=lambda: _alphamissense_or_empty(accession, aa_position, aa_alt_one_letter),
            persist_fixture=True,
        )

    variant_pdb = None
    variant_method: str = "none"
    if sequence and aa_position and aa_alt_one_letter and 1 <= aa_position <= len(sequence):
        async def fetcher_var() -> dict:
            mut_seq = sequence[:aa_position - 1] + aa_alt_one_letter + sequence[aa_position:]
            excised, _ = _excise_around_variant(mut_seq, aa_position, window=240)
            try:
                pdb = await _esmfold(excised)
                return {"pdb": pdb, "method": "esmfold", "excerpt_length": len(excised)}
            except Exception as exc:
                log.warning("esmfold variant fold failed: %s", exc)
                return {}
        var = await cached_fetch(variant_key_str=vk, source="esmfold_variant", fetcher=fetcher_var, persist_fixture=True)
        if var.get("pdb"):
            variant_pdb = var.get("pdb")
            variant_method = "esmfold"

    am_score = (am_data or {}).get("score") if am_data else None
    am_class = (am_data or {}).get("class") if am_data else None
    ddg = _crude_ddg_from_alphamissense(am_score)

    return StructuralAnalysis(
        uniprot_accession=accession,
        af_pdb_url=(ref or {}).get("url") or af_pdb_url(accession),
        af_mean_plddt=ref.get("mean_plddt") if ref else None,
        variant_pdb_url=None,  # served via /api/jobs/{id}/structure if needed
        variant_method=variant_method,
        rmsd_angstrom=None,  # left None when we don't run a CA alignment
        alphamissense_score=am_score,
        alphamissense_class=am_class,
        ddg_kcal_mol=ddg,
        domain_at_position=domain_at_position,
        in_active_site=in_active_site,
    )


async def _alphamissense_or_empty(accession: str, position: int, alt: str) -> dict:
    res = await _alphamissense_lookup(accession, position, alt)
    return res or {}
