"""Population & clinical databases: gnomAD v4, ClinVar (NCBI), UniProt, InterPro, LOVD."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from backend.cache.store import cached_fetch, variant_key
from backend.config import get_settings
from shared.schemas import ClinVarRecord, GnomadFreq, VariantInput


log = logging.getLogger(__name__)

GNOMAD_URL = "https://gnomad.broadinstitute.org/api"

GNOMAD_QUERY = """
query VariantInfo($variantId: String!, $datasetId: DatasetId!) {
  variant(variantId: $variantId, dataset: $datasetId) {
    variant_id
    rsid
    exome { ac an af populations { id ac an } homozygote_count hemizygote_count flags }
    genome { ac an af populations { id ac an } homozygote_count hemizygote_count flags }
  }
}
"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=8))
async def _gnomad_post(variant_id: str, dataset: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            GNOMAD_URL,
            json={"query": GNOMAD_QUERY, "variables": {"variantId": variant_id, "datasetId": dataset}},
        )
        r.raise_for_status()
        return r.json()


async def fetch_gnomad(v: VariantInput) -> GnomadFreq:
    chrom = v.chrom.lstrip("chr")
    variant_id = f"{chrom}-{v.pos}-{v.ref}-{v.alt}"
    dataset = "gnomad_r4" if v.assembly == "GRCh38" else "gnomad_r2_1"
    vk = variant_key(v.chrom, v.pos, v.ref, v.alt, v.assembly)

    raw = await cached_fetch(
        variant_key_str=vk,
        source="gnomad",
        fetcher=lambda: _gnomad_post(variant_id, dataset),
        persist_fixture=True,
    )

    data = (raw or {}).get("data") or {}
    var = data.get("variant")
    if not var:
        return GnomadFreq(notes="absent from gnomAD", has_amr=False)

    pops: dict[str, float] = {}
    af_global = None
    n_hom = 0
    n_hemi = 0
    flags: list[str] = []
    for which in ("exome", "genome"):
        block = var.get(which) or {}
        if block.get("af") is not None:
            af_global = max(af_global or 0.0, block["af"])
        for p in block.get("populations") or []:
            an = p.get("an") or 0
            ac = p.get("ac") or 0
            if an > 0:
                pops[p["id"]] = max(pops.get(p["id"], 0.0), ac / an)
        n_hom += block.get("homozygote_count") or 0
        n_hemi += block.get("hemizygote_count") or 0
        for f in block.get("flags") or []:
            if f not in flags:
                flags.append(f)

    has_amr = bool(pops.get("amr") or pops.get("AMR"))
    notes = None
    if not has_amr:
        notes = "No Latin-American (amr) frequency data — gnomAD v4 representation is limited; lean on computational predictors for ancestry-matched inference."

    return GnomadFreq(
        af_global=af_global,
        af_populations=pops,
        homozygote_count=n_hom,
        hemizygote_count=n_hemi,
        flags=flags,
        has_amr=has_amr,
        notes=notes,
    )


# ---------- ClinVar via NCBI E-utilities ----------

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=6))
async def _ncbi_get(path: str, params: dict[str, Any]) -> dict:
    s = get_settings()
    if s._looks_real(s.ncbi_api_key):
        params["api_key"] = s.ncbi_api_key
    params.setdefault("email", s.ncbi_email)
    params.setdefault("tool", "hepvar")
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{NCBI_BASE}/{path}", params=params)
        r.raise_for_status()
        return r.json()


async def fetch_clinvar(v: VariantInput, gene: str | None, hgvs_p: str | None) -> ClinVarRecord:
    vk = variant_key(v.chrom, v.pos, v.ref, v.alt, v.assembly)
    chrom = v.chrom.lstrip("chr")

    # Build a few alternative queries; first hit wins.
    queries: list[str] = []
    if gene and hgvs_p:
        queries.append(f"{gene}[gene] AND {hgvs_p.split(':')[-1]}")
    queries.append(f"{chrom}[chr] AND {v.pos}[chrpos]")
    if gene:
        queries.append(f"{gene}[gene] AND single_gene[Properties]")

    async def fetcher() -> dict:
        for q in queries:
            try:
                resp = await _ncbi_get("esearch.fcgi", {"db": "clinvar", "term": q, "retmode": "json", "retmax": 5})
            except Exception:
                continue
            ids = (resp.get("esearchresult") or {}).get("idlist") or []
            if not ids:
                continue
            try:
                summary = await _ncbi_get("esummary.fcgi", {"db": "clinvar", "id": ",".join(ids), "retmode": "json"})
            except Exception:
                continue
            res = (summary.get("result") or {})
            for cid in ids:
                doc = res.get(cid)
                if not doc:
                    continue
                germ = (doc.get("germline_classification") or {})
                trait_set = germ.get("trait_set") or []
                conditions = [t.get("trait_name") for t in trait_set if t.get("trait_name")]
                rs = germ.get("review_status", "")
                stars = {
                    "practice guideline": 4,
                    "reviewed by expert panel": 3,
                    "criteria provided, multiple submitters, no conflicts": 2,
                    "criteria provided, conflicting interpretations": 1,
                    "criteria provided, single submitter": 1,
                    "no assertion criteria provided": 0,
                }.get(rs.lower().strip(), None)
                return {
                    "clinical_significance": germ.get("description"),
                    "review_status": rs,
                    "star_rating": stars,
                    "conditions": conditions,
                    "last_evaluated": germ.get("last_evaluated"),
                    "accession": doc.get("accession"),
                }
        return {}

    raw = await cached_fetch(variant_key_str=vk, source="clinvar", fetcher=fetcher, persist_fixture=True)
    return ClinVarRecord(**raw) if raw else ClinVarRecord()


# ---------- UniProt features ----------

@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=6))
async def _uniprot_get(accession: str) -> dict:
    url = f"https://rest.uniprot.org/uniprotkb/{accession}.json"
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.json()


async def fetch_uniprot(v: VariantInput, accession: str | None) -> dict:
    if not accession:
        return {}
    vk = variant_key(v.chrom, v.pos, v.ref, v.alt, v.assembly)
    raw = await cached_fetch(
        variant_key_str=vk,
        source="uniprot",
        fetcher=lambda: _uniprot_get(accession),
        persist_fixture=True,
    )
    if not raw:
        return {}
    features = raw.get("features") or []
    domains = [f for f in features if f.get("type") in ("Domain", "Region", "Motif")]
    active_sites = [f for f in features if f.get("type") in ("Active site", "Binding site")]
    return {
        "accession": accession,
        "name": (raw.get("proteinDescription") or {}).get("recommendedName", {}).get("fullName", {}).get("value"),
        "length": (raw.get("sequence") or {}).get("length"),
        "sequence": (raw.get("sequence") or {}).get("value"),
        "domains": [
            {"description": d.get("description"), "begin": (d.get("location") or {}).get("start", {}).get("value"),
             "end": (d.get("location") or {}).get("end", {}).get("value"), "type": d.get("type")}
            for d in domains
        ],
        "active_sites": [
            {"description": s.get("description"),
             "position": (s.get("location") or {}).get("start", {}).get("value")}
            for s in active_sites
        ],
        "function": next((c.get("texts", [{}])[0].get("value") for c in raw.get("comments") or [] if c.get("commentType") == "FUNCTION"), None),
    }


# ---------- InterPro ----------

@retry(stop=stop_after_attempt(2), wait=wait_exponential_jitter(initial=1, max=4))
async def _interpro_get(accession: str) -> dict:
    url = f"https://www.ebi.ac.uk/interpro/api/entry/all/protein/UniProt/{accession}/"
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(url)
        if r.status_code == 404:
            return {"results": []}
        r.raise_for_status()
        return r.json()


async def fetch_interpro(v: VariantInput, accession: str | None) -> dict:
    if not accession:
        return {}
    vk = variant_key(v.chrom, v.pos, v.ref, v.alt, v.assembly)
    raw = await cached_fetch(
        variant_key_str=vk,
        source="interpro",
        fetcher=lambda: _interpro_get(accession),
        persist_fixture=True,
    )
    out = []
    for entry in (raw or {}).get("results") or []:
        meta = entry.get("metadata") or {}
        loci = []
        for prot in entry.get("proteins") or []:
            for frag_set in prot.get("entry_protein_locations") or []:
                for frag in frag_set.get("fragments") or []:
                    loci.append({"start": frag.get("start"), "end": frag.get("end")})
        out.append({
            "accession": meta.get("accession"),
            "name": meta.get("name"),
            "type": meta.get("type"),
            "source_database": meta.get("source_database"),
            "fragments": loci,
        })
    return {"entries": out}


# ---------- LOVD (locus-specific) ----------

async def fetch_lovd(v: VariantInput, gene: str | None, hgvs_c: str | None = None) -> dict:
    """Best-effort LOVD shared-DB lookup via cDNA notation.

    LOVD shared (databases.lovd.nl) blocks cloud/datacenter IPs with a 302→403
    redirect. When it succeeds (local/VPN), queries by VariantOnTranscript/DNA
    using the short cDNA suffix (e.g. 'c.3207C>A'). Falls back to genomic
    position if hgvs_c is unavailable.
    """
    if not gene:
        return {}
    vk = variant_key(v.chrom, v.pos, v.ref, v.alt, v.assembly)

    async def fetcher() -> dict:
        url = f"https://databases.lovd.nl/shared/api/rest.php/variants/{gene}"
        # Prefer cDNA notation (short suffix after ':') — more reliable than genomic pos
        if hgvs_c:
            short_c = hgvs_c.split(":")[-1]  # e.g. "c.3207C>A"
            params = {"search_VariantOnTranscript/DNA": short_c, "format": "application/json"}
        else:
            params = {"search_position": f"g.{v.pos}", "format": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=False) as c:
                r = await c.get(url, params=params,
                                headers={"User-Agent": f"hepvar/0.1 (contact: {get_settings().ncbi_email})"})
                # 302/403 = LOVD blocking cloud IP — degrade gracefully
                if r.status_code in (302, 403) or r.status_code != 200:
                    return {}
                text = r.text.strip()
                if not text or text.startswith("<"):
                    return {}
                return {"raw": text[:8000]}
        except Exception:
            return {}

    raw = await cached_fetch(variant_key_str=vk, source="lovd", fetcher=fetcher, persist_fixture=True)
    return raw or {}
