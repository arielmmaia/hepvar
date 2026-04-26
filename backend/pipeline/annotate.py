"""Ensembl VEP REST annotation.

Returns: VEPAnnotation with HGVS c./p., consequence, rsID, UniProt accession, SIFT, PolyPhen, CADD.
"""
from __future__ import annotations

import logging
import re

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from backend.cache.store import cached_fetch, variant_key
from backend.pipeline.aa_properties import compare as aa_compare
from shared.schemas import TranscriptConsequence, VEPAnnotation, VariantInput


log = logging.getLogger(__name__)

VEP_GRCH38 = "https://rest.ensembl.org"
VEP_GRCH37 = "https://grch37.rest.ensembl.org"

THREE_TO_ONE = {
    "Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C",
    "Gln": "Q", "Glu": "E", "Gly": "G", "His": "H", "Ile": "I",
    "Leu": "L", "Lys": "K", "Met": "M", "Phe": "F", "Pro": "P",
    "Ser": "S", "Thr": "T", "Trp": "W", "Tyr": "Y", "Val": "V",
    "Ter": "*", "Sec": "U", "Pyl": "O",
}


def parse_hgvs_p(hgvs_p: str | None) -> dict | None:
    if not hgvs_p:
        return None
    m = re.search(r"p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2}|\*)", hgvs_p)
    if not m:
        return None
    ref3, pos_s, alt3 = m.group(1), m.group(2), m.group(3)
    return {
        "ref": ref3,
        "alt": alt3,
        "position": int(pos_s),
        "ref1letter": THREE_TO_ONE.get(ref3, "X"),
        "alt1letter": THREE_TO_ONE.get(alt3, alt3 if alt3 == "*" else "X"),
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=8))
async def _vep_call(server: str, region: str, allele: str) -> list:
    url = f"{server}/vep/human/region/{region}/{allele}"
    params = {
        "hgvs": 1, "uniprot": 1, "domains": 1, "canonical": 1,
        "CADD": 1, "AlphaMissense": 1, "numbers": 1, "protein": 1,
        "transcript_version": 1,
    }
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(url, params=params, headers={"Accept": "application/json"})
        r.raise_for_status()
        return r.json()


async def annotate_variant(v: VariantInput) -> VEPAnnotation:
    """Returns a populated VEPAnnotation. Raises on hard VEP failure (orchestrator catches)."""
    server = VEP_GRCH38 if v.assembly == "GRCh38" else VEP_GRCH37
    chrom = v.chrom.lstrip("chr")
    region = f"{chrom}:{v.pos}-{v.pos}"
    allele = v.alt
    vk = variant_key(v.chrom, v.pos, v.ref, v.alt, v.assembly)

    payload = await cached_fetch(
        variant_key_str=vk,
        source="vep",
        fetcher=lambda: _vep_call(server, region, allele),
        persist_fixture=True,
    )
    if not payload:
        return VEPAnnotation()

    record = payload[0] if isinstance(payload, list) else payload
    txs = record.get("transcript_consequences") or []
    canonical = next((t for t in txs if t.get("canonical")), txs[0] if txs else {})

    hgvs_c = canonical.get("hgvsc")
    hgvs_p = canonical.get("hgvsp")
    aa_change = parse_hgvs_p(hgvs_p)

    # Capture every protein-coding transcript so the dashboard can show isoform
    # differences. Same genomic change → different cDNA position / different AA
    # numbering across isoforms (e.g. ABCB4 c.3128 in the canonical = c.2987 in
    # the shorter isoform, p.Tyr1043Cys vs p.Tyr996Cys).
    transcripts: list[TranscriptConsequence] = []
    for t in txs:
        if not t.get("transcript_id"):
            continue
        p = parse_hgvs_p(t.get("hgvsp"))
        transcripts.append(TranscriptConsequence(
            transcript_id=t.get("transcript_id"),
            transcript_biotype=t.get("biotype"),
            gene_symbol=t.get("gene_symbol"),
            canonical=bool(t.get("canonical")),
            mane_select=t.get("mane_select") or t.get("mane_plus_clinical"),
            refseq_match=t.get("refseq_match"),
            hgvs_c=t.get("hgvsc"),
            hgvs_p=t.get("hgvsp"),
            consequence=(t.get("consequence_terms") or [None])[0],
            impact=t.get("impact"),
            aa_position=p.get("position") if p else None,
            aa_ref=p.get("ref1letter") if p else None,
            aa_alt=p.get("alt1letter") if p else None,
        ))
    # Sort: canonical first, then MANE-select, then alphabetical.
    transcripts.sort(key=lambda x: (not x.canonical, not bool(x.mane_select), x.transcript_id or ""))

    rs_id = None
    clinvar_id = None
    for cv in record.get("colocated_variants", []) or []:
        if cv.get("id", "").startswith("rs") and not rs_id:
            rs_id = cv["id"]
        if cv.get("var_synonyms", {}).get("ClinVar"):
            clinvar_id = cv["var_synonyms"]["ClinVar"][0]

    raw_accession = (canonical.get("swissprot") or [None])[0]
    # VEP returns versioned accessions like "P21439.229"; UniProt REST 303s on those.
    clean_accession = raw_accession.split(".")[0].split("-")[0] if raw_accession else None

    # Physicochemical comparison of the WT vs variant amino acid (missense only).
    aa_substitution = None
    if aa_change:
        aa_substitution = aa_compare(aa_change.get("ref1letter"), aa_change.get("alt1letter"))

    return VEPAnnotation(
        gene_symbol=canonical.get("gene_symbol"),
        transcript_id=canonical.get("transcript_id"),
        hgvs_c=hgvs_c,
        hgvs_p=hgvs_p,
        consequence=(canonical.get("consequence_terms") or [None])[0],
        impact=canonical.get("impact"),
        rs_id=rs_id,
        clinvar_id=clinvar_id,
        uniprot_accession=clean_accession,
        sift={"score": canonical.get("sift_score"), "prediction": canonical.get("sift_prediction")},
        polyphen={"score": canonical.get("polyphen_score"), "prediction": canonical.get("polyphen_prediction")},
        cadd=canonical.get("cadd_phred"),
        aa_change=aa_change,
        aa_substitution=aa_substitution,
        transcripts=transcripts,
    )
