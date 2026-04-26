"""Multi-alias, multilingual literature search across PubMed and Europe PMC.

Languages searched: English, Portuguese, Spanish, Italian, French.
Why: rare-disease case reports of variants seen in Latin-American / non-Anglophone
patients are frequently published only in regional journals in Romance languages
and never submitted to ClinVar curation.
"""
from __future__ import annotations

import logging
from typing import Iterable

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from backend.cache.store import cached_fetch, stable_hash, variant_key
from backend.config import get_settings
from shared.schemas import LiteratureHit, VariantInput, VEPAnnotation


log = logging.getLogger(__name__)

LANGUAGES = ["en", "pt", "es", "it", "fr"]
EUROPEPMC_LANG_CODES = {
    "en": "english", "pt": "portuguese", "es": "spanish", "it": "italian", "fr": "french",
}


def build_aliases(v: VariantInput, ann: VEPAnnotation | None) -> list[str]:
    """Per-alias queries (unquoted, simple). Each is fired as its own search."""
    aliases: list[str] = []
    if ann and ann.gene_symbol:
        gene = ann.gene_symbol
        if ann.aa_change:
            ac = ann.aa_change
            short1 = f"{ac['ref1letter']}{ac['position']}{ac['alt1letter']}"  # e.g. Y1043C
            short3 = f"{ac['ref']}{ac['position']}{ac['alt']}"                 # e.g. Tyr1043Cys
            aliases.extend([
                f"{gene} {short1}",
                f"{gene} {short3}",
                f"{gene} p.{short1}",
                f"{gene} p.{short3}",
            ])
        if ann.hgvs_p:
            short_p = ann.hgvs_p.split(":")[-1]  # "p.Tyr1043Cys"
            aliases.append(f"{gene} {short_p}")
        if ann.hgvs_c:
            short_c = ann.hgvs_c.split(":")[-1]
            aliases.append(f"{gene} {short_c}")
        if ann.rs_id:
            aliases.append(ann.rs_id)
        # broader gene-level fallback so we always have *some* signal
        aliases.append(f"{gene} AND (mutation OR variant OR \"case report\" OR \"PFIC\" OR \"LPAC\")")

    aliases.append(f"{v.chrom}:{v.pos}")
    return list(dict.fromkeys(aliases))


# ---------- Europe PMC ----------

@retry(stop=stop_after_attempt(2), wait=wait_exponential_jitter(initial=1, max=4))
async def _europepmc_search(query: str, page_size: int = 10) -> dict:
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {
        "query": query, "format": "json", "pageSize": page_size,
        "resultType": "core",
    }
    async with httpx.AsyncClient(timeout=25) as c:
        r = await c.get(url, params=params)
        r.raise_for_status()
        return r.json()


def _parse_europepmc_hit(h: dict) -> LiteratureHit:
    title = (h.get("title") or "").strip()
    abstract = (h.get("abstractText") or None)
    journal = ((h.get("journalInfo") or {}).get("journal") or {}).get("title")
    year_raw = h.get("pubYear")
    year = int(year_raw) if year_raw and str(year_raw).isdigit() else None
    lang = (h.get("language") or "en").lower()[:2]
    keys = " ".join(filter(None, [title, abstract or ""])).lower()
    return LiteratureHit(
        pmid=h.get("pmid"),
        doi=h.get("doi"),
        title=title or "(no title)",
        journal=journal,
        year=year,
        abstract=abstract,
        language=lang,
        is_case_report=("case report" in keys or "caso clinico" in keys or "caso clínico" in keys
                        or "relato de caso" in keys or "rapport de cas" in keys),
        is_functional_study=("functional" in keys or "transport assay" in keys or "in vitro" in keys
                              or "expression assay" in keys),
    )


async def search_europepmc_multilingual(aliases: list[str]) -> list[LiteratureHit]:
    hits: list[LiteratureHit] = []
    seen: set[str] = set()

    # 1) Each alias fires as its own search (more reliable than complex OR queries).
    for alias in aliases[:8]:
        try:
            raw = await _europepmc_search(alias, page_size=8)
            for h in (raw.get("resultList") or {}).get("result") or []:
                hit = _parse_europepmc_hit(h)
                k = hit.pmid or hit.doi or hit.title
                if k in seen:
                    continue
                seen.add(k)
                hit.matched_aliases = [alias]
                hits.append(hit)
        except Exception as exc:
            log.warning("europepmc alias %r failed: %s", alias, exc)

    # 2) Per-language gene-level queries to surface non-English regional case reports.
    gene_alias = next((a for a in aliases if " " not in a or a.split()[0].isupper()), None)
    gene_term = aliases[0].split()[0] if aliases else None  # heuristically the gene symbol
    if gene_term:
        for lang in ("pt", "es", "it", "fr"):
            q = f"({gene_term}) AND ({EUROPEPMC_LANG_CODES[lang]}[language])"
            try:
                raw = await _europepmc_search(q, page_size=6)
                for h in (raw.get("resultList") or {}).get("result") or []:
                    hit = _parse_europepmc_hit(h)
                    hit.language = lang
                    k = hit.pmid or hit.doi or hit.title
                    if k in seen:
                        continue
                    seen.add(k)
                    hits.append(hit)
            except Exception as exc:
                log.warning("europepmc %s search failed: %s", lang, exc)
    return hits


# ---------- PubMed Entrez ----------

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@retry(stop=stop_after_attempt(2), wait=wait_exponential_jitter(initial=1, max=4))
async def _pubmed_search(query: str) -> list[str]:
    s = get_settings()
    params = {"db": "pubmed", "term": query, "retmax": 20, "retmode": "json", "tool": "hepvar", "email": s.ncbi_email}
    if s._looks_real(s.ncbi_api_key):
        params["api_key"] = s.ncbi_api_key
    async with httpx.AsyncClient(timeout=25) as c:
        r = await c.get(f"{NCBI_BASE}/esearch.fcgi", params=params)
        r.raise_for_status()
        return ((r.json().get("esearchresult") or {}).get("idlist") or [])


@retry(stop=stop_after_attempt(2), wait=wait_exponential_jitter(initial=1, max=4))
async def _pubmed_summary(ids: list[str]) -> dict:
    if not ids:
        return {}
    s = get_settings()
    params = {"db": "pubmed", "id": ",".join(ids), "retmode": "json", "tool": "hepvar", "email": s.ncbi_email}
    if s._looks_real(s.ncbi_api_key):
        params["api_key"] = s.ncbi_api_key
    async with httpx.AsyncClient(timeout=25) as c:
        r = await c.get(f"{NCBI_BASE}/esummary.fcgi", params=params)
        r.raise_for_status()
        return r.json()


async def search_pubmed(aliases: list[str]) -> list[LiteratureHit]:
    if not aliases:
        return []
    # Per-alias queries; collect IDs then resolve once.
    all_ids: list[str] = []
    seen_ids: set[str] = set()
    for alias in aliases[:6]:
        try:
            ids = await _pubmed_search(alias)
            for i in ids:
                if i not in seen_ids:
                    seen_ids.add(i)
                    all_ids.append(i)
        except Exception as exc:
            log.warning("pubmed alias %r failed: %s", alias, exc)
    if not all_ids:
        return []
    try:
        summary = await _pubmed_summary(all_ids[:20])
    except Exception as exc:
        log.warning("pubmed summary failed: %s", exc)
        return []
    ids = all_ids
    res = (summary.get("result") or {})
    out: list[LiteratureHit] = []
    for pmid in ids[:15]:
        doc = res.get(pmid)
        if not doc:
            continue
        title = doc.get("title", "(no title)")
        keys = title.lower()
        out.append(LiteratureHit(
            pmid=pmid,
            doi=next((aid["value"] for aid in doc.get("articleids", []) if aid.get("idtype") == "doi"), None),
            title=title,
            journal=doc.get("fulljournalname") or doc.get("source"),
            year=int(doc["pubdate"].split()[0]) if doc.get("pubdate", "").split() and doc["pubdate"].split()[0].isdigit() else None,
            language=(doc.get("lang") or ["eng"])[0][:2].replace("eng", "en").replace("por", "pt").replace("spa", "es").replace("ita", "it").replace("fra", "fr"),
            is_case_report=("case report" in keys),
            is_functional_study=("functional" in keys),
            matched_aliases=aliases[:6],
        ))
    return out


def _rank(hits: Iterable[LiteratureHit]) -> list[LiteratureHit]:
    out = list(hits)
    for h in out:
        score = 0.0
        if h.is_functional_study:
            score += 3.0
        if h.is_case_report:
            score += 2.0
        if h.language != "en":
            score += 1.5  # bonus for non-English literature (the equity premise)
        if h.year and h.year >= 2018:
            score += 1.0
        score += min(len(h.abstract or ""), 800) / 800
        h.relevance_score = round(score, 2)
    out.sort(key=lambda h: h.relevance_score, reverse=True)
    return out[:25]


async def search_literature(v: VariantInput, ann: VEPAnnotation | None) -> list[LiteratureHit]:
    aliases = build_aliases(v, ann)
    vk = variant_key(v.chrom, v.pos, v.ref, v.alt, v.assembly)

    async def fetcher() -> dict:
        epmc = await search_europepmc_multilingual(aliases)
        pm = await search_pubmed(aliases)
        # de-dup pmid/title
        seen: set[str] = set()
        merged: list[LiteratureHit] = []
        for h in epmc + pm:
            k = (h.pmid or h.doi or h.title).lower()
            if k in seen:
                continue
            seen.add(k)
            merged.append(h)
        ranked = _rank(merged)
        return {"hits": [h.model_dump() for h in ranked], "alias_hash": stable_hash(aliases)}

    raw = await cached_fetch(variant_key_str=vk, source="literature", fetcher=fetcher, persist_fixture=True)
    return [LiteratureHit(**h) for h in (raw or {}).get("hits", [])]
