"""Liver-specific context: gene panel lookup + GTEx liver TPM + Human Protein Atlas + Reactome + KEGG."""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from backend.cache.store import cached_fetch, variant_key
from backend.config import get_settings
from shared.schemas import LiverContext, VariantInput


log = logging.getLogger(__name__)


@lru_cache
def _load_panel() -> dict[str, dict]:
    s = get_settings()
    p = Path(s.gene_panel_path)
    raw = json.loads(p.read_text())
    return {g["symbol"]: g for g in raw.get("genes", [])}


@retry(stop=stop_after_attempt(2), wait=wait_exponential_jitter(initial=1, max=4))
async def _gtex_median(gene_symbol: str) -> float | None:
    url = "https://gtexportal.org/api/v2/expression/medianGeneExpression"
    params = {"gencodeId": gene_symbol, "tissueSiteDetailId": "Liver", "datasetId": "gtex_v8"}
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(url, params=params)
        if r.status_code != 200:
            return None
        for d in (r.json().get("data") or []):
            if d.get("tissueSiteDetailId") == "Liver":
                return d.get("median")
    return None


@retry(stop=stop_after_attempt(2), wait=wait_exponential_jitter(initial=1, max=4))
async def _hpa_liver(gene_symbol: str) -> str | None:
    url = f"https://www.proteinatlas.org/api/search_download.json"
    params = {"search": gene_symbol, "format": "json", "columns": "g,t_RNA_liver,rnats_liver", "compress": "no"}
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(url, params=params)
            if r.status_code != 200:
                return None
            data = r.json()
        if isinstance(data, list) and data:
            row = next((d for d in data if d.get("Gene") == gene_symbol), data[0])
            tpm = row.get("RNA tissue specific NX (Liver)") or row.get("RNA liver")
            return str(tpm) if tpm else None
    except Exception:
        return None
    return None


@retry(stop=stop_after_attempt(2), wait=wait_exponential_jitter(initial=1, max=4))
async def _reactome_pathways(gene_symbol: str) -> list[str]:
    url = f"https://reactome.org/ContentService/data/mapping/UniProt/{gene_symbol}/pathways"
    params = {"species": 9606}
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(url, params=params)
            if r.status_code != 200:
                return []
            data = r.json()
            return [p.get("displayName") for p in data if p.get("displayName")][:8]
    except Exception:
        return []


@retry(stop=stop_after_attempt(2), wait=wait_exponential_jitter(initial=1, max=4))
async def _kegg_pathways(gene_symbol: str) -> list[str]:
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"https://rest.kegg.jp/find/genes/{gene_symbol}")
            if r.status_code != 200:
                return []
            text = r.text
        # parse "hsa:5243\tgene name; description" lines, take first hsa:
        gene_id = None
        for line in text.splitlines():
            if line.startswith("hsa:"):
                gene_id = line.split("\t")[0]
                break
        if not gene_id:
            return []
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"https://rest.kegg.jp/link/pathway/{gene_id}")
            if r.status_code != 200:
                return []
            paths = []
            for line in r.text.splitlines():
                parts = line.split("\t")
                if len(parts) == 2:
                    paths.append(parts[1].replace("path:", ""))
        # resolve names (one batched call)
        if not paths:
            return []
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"https://rest.kegg.jp/list/pathway/hsa")
            if r.status_code != 200:
                return paths
            names: dict[str, str] = {}
            for line in r.text.splitlines():
                parts = line.split("\t")
                if len(parts) == 2:
                    names[parts[0].replace("path:", "")] = parts[1]
        return [names.get(p, p) for p in paths][:8]
    except Exception:
        return []


async def fetch_liver_context(v: VariantInput, gene_symbol: str | None) -> LiverContext:
    if not gene_symbol:
        return LiverContext()
    panel = _load_panel()
    entry = panel.get(gene_symbol)

    vk = variant_key(v.chrom, v.pos, v.ref, v.alt, v.assembly)

    async def fetcher() -> dict:
        gtex = await _gtex_median(gene_symbol)
        hpa = await _hpa_liver(gene_symbol)
        reactome = await _reactome_pathways(gene_symbol)
        kegg = await _kegg_pathways(gene_symbol)
        return {"gtex": gtex, "hpa": hpa, "reactome": reactome, "kegg": kegg}

    raw = await cached_fetch(variant_key_str=vk, source="liver_context", fetcher=fetcher, persist_fixture=True)
    return LiverContext(
        in_panel=entry is not None,
        panel_entry=entry,
        gtex_liver_tpm=raw.get("gtex") if raw else None,
        hpa_liver_expression=raw.get("hpa") if raw else None,
        reactome_pathways=(raw or {}).get("reactome", []) or [],
        kegg_pathways=(raw or {}).get("kegg", []) or [],
    )
