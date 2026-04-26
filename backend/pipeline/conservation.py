"""Cross-species conservation at the variant residue, via Ensembl Compara."""
from __future__ import annotations

import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from backend.cache.store import cached_fetch, variant_key
from shared.schemas import ConservationPanel, OrthologResidue, VariantInput


log = logging.getLogger(__name__)


# Curated 'representative' species ladder spanning ~1.5 Bn years of vertebrate
# evolution. Used to pick a clinically-relevant subset out of the ~190 vertebrate
# orthologues Ensembl returns.
REPRESENTATIVE_SPECIES: list[tuple[str, str]] = [
    ("pan_troglodytes",          "Chimpanzee"),
    ("gorilla_gorilla",          "Gorilla"),
    ("pongo_abelii",             "Orangutan"),
    ("macaca_mulatta",           "Rhesus macaque"),
    ("callithrix_jacchus",       "Marmoset"),
    ("mus_musculus",             "Mouse"),
    ("rattus_norvegicus",        "Rat"),
    ("oryctolagus_cuniculus",    "Rabbit"),
    ("canis_lupus_familiaris",   "Dog"),
    ("bos_taurus",               "Cow"),
    ("sus_scrofa",               "Pig"),
    ("equus_caballus",           "Horse"),
    ("monodelphis_domestica",    "Opossum"),
    ("ornithorhynchus_anatinus", "Platypus"),
    ("gallus_gallus",            "Chicken"),
    ("anolis_carolinensis",      "Anolis lizard"),
    ("xenopus_tropicalis",       "Western clawed frog"),
    ("danio_rerio",              "Zebrafish"),
    ("oryzias_latipes",          "Medaka"),
    ("petromyzon_marinus",       "Sea lamprey"),
    ("ciona_intestinalis",       "Sea squirt"),
    ("drosophila_melanogaster",  "Fruit fly"),
    ("caenorhabditis_elegans",   "C. elegans"),
    ("saccharomyces_cerevisiae", "Baker's yeast"),
]


@retry(stop=stop_after_attempt(2), wait=wait_exponential_jitter(initial=1, max=6))
async def _ensembl_homology(gene_symbol: str) -> dict:
    url = f"https://rest.ensembl.org/homology/symbol/human/{gene_symbol}"
    params = {"type": "orthologues", "format": "full", "aligned": 1}
    async with httpx.AsyncClient(timeout=45) as c:
        r = await c.get(url, params=params, headers={"Accept": "application/json"})
        r.raise_for_status()
        return r.json()


def _alignment_index_for_residue(source_align_seq: str, residue: int) -> int | None:
    """Map a 1-based residue number on the human protein to its index in the
    aligned (gapped) source sequence."""
    counter = 0
    for i, ch in enumerate(source_align_seq):
        if ch != "-":
            counter += 1
            if counter == residue:
                return i
    return None


async def fetch_conservation(
    variant: VariantInput,
    gene_symbol: str | None,
    aa_position: int | None,
    aa_ref: str | None,
) -> ConservationPanel | None:
    if not gene_symbol or not aa_position:
        return None

    vk = variant_key(variant.chrom, variant.pos, variant.ref, variant.alt, variant.assembly)

    async def fetcher() -> dict:
        try:
            data = await _ensembl_homology(gene_symbol)
        except Exception as exc:
            log.warning("ensembl homology failed: %s", exc)
            return {"error": str(exc)}
        entries = data.get("data") or []
        if not entries:
            return {"error": "no homology data"}
        homologies = entries[0].get("homologies") or []
        if not homologies:
            return {"error": "no orthologues returned"}

        source_align = homologies[0].get("source", {}).get("align_seq") or ""
        align_idx = _alignment_index_for_residue(source_align, aa_position)
        if align_idx is None:
            return {"error": "could not map variant position to alignment"}

        wanted = {sp: common for sp, common in REPRESENTATIVE_SPECIES}
        # Some species have multiple paralogs in Ensembl Compara (C. elegans
        # often has ~8 ABC transporter homologs). Keep the best (highest
        # perc_id) match per species, with a tiebreaker preferring a residue
        # that matches human.
        best_per_species: dict[str, dict] = {}
        for h in homologies:
            tgt = h.get("target", {})
            sp = tgt.get("species")
            if sp not in wanted:
                continue
            tgt_seq = tgt.get("align_seq") or ""
            if align_idx >= len(tgt_seq):
                continue
            aa_at = tgt_seq[align_idx]
            cand = {
                "species": sp,
                "common_name": wanted[sp],
                "residue": aa_at if aa_at != "-" else None,
                "is_gap": aa_at == "-",
                "matches_human": (aa_at == (aa_ref or "")),
                "perc_id": tgt.get("perc_id") or 0.0,
            }
            existing = best_per_species.get(sp)
            if existing is None:
                best_per_species[sp] = cand
                continue
            # Prefer match-to-human first, then higher perc_id.
            if cand["matches_human"] and not existing["matches_human"]:
                best_per_species[sp] = cand
            elif cand["matches_human"] == existing["matches_human"] and cand["perc_id"] > existing["perc_id"]:
                best_per_species[sp] = cand

        # Order according to REPRESENTATIVE_SPECIES (evolutionary ladder)
        order = {sp: i for i, (sp, _) in enumerate(REPRESENTATIVE_SPECIES)}
        species_records = sorted(best_per_species.values(), key=lambda r: order.get(r["species"], 999))
        return {"species": species_records, "human_residue": aa_ref}

    raw = await cached_fetch(variant_key_str=vk, source="conservation", fetcher=fetcher, persist_fixture=True)
    if not raw or "error" in raw:
        return ConservationPanel(gene_symbol=gene_symbol, variant_position=aa_position, human_residue=aa_ref)

    species = [OrthologResidue(**r) for r in raw.get("species", [])]
    n = len(species)
    n_match = sum(1 for s in species if s.matches_human)
    pct = (100.0 * n_match / n) if n > 0 else None
    return ConservationPanel(
        gene_symbol=gene_symbol,
        variant_position=aa_position,
        human_residue=aa_ref,
        n_orthologs=n,
        n_match=n_match,
        pct_conserved_at_position=round(pct, 1) if pct is not None else None,
        species=species,
    )
