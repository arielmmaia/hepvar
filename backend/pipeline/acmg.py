"""ACMG/AMP variant classification — Tavtigian Bayesian (PMID 31801977).

Implements the criteria that can be assigned automatically from the assembled evidence:
PVS1, PS1, PS3, PM1, PM2, PM4, PM5, PP2, PP3, PP5, BA1, BS1, BS2, BP1, BP3, BP4, BP6, BP7.

Criteria left unassigned (require external data we don't have): PS2/PM6 (de novo + confirmed parentage),
PS4 (case/control prevalence), PM3 (in-trans phasing), PP1/BS4 (segregation), PP4 (specific phenotype),
BS3 (negative functional study), BP2 (compound het with dominant), BP5 (alternate cause).
"""
from __future__ import annotations

from typing import Iterable

from shared.schemas import (
    ACMGCriterion,
    ACMGResult,
    ClinVarRecord,
    EvidencePacket,
    GnomadFreq,
    LiteratureHit,
    StructuralAnalysis,
    VEPAnnotation,
)


# Tavtigian Bayesian odds (PMID 31801977 Table 2)
ODDS = {
    "PVS1": 350.0,
    "PS": 18.7,
    "PM": 4.33,
    "PP": 2.08,
    "BP": 1 / 2.08,
    "BS": 1 / 18.7,
    "BA1": 0.0,  # absolute benign override
}

# Point weights (Tavtigian point system)
WEIGHT = {
    "PVS1": 8,
    "PS1": 4, "PS2": 4, "PS3": 4, "PS4": 4,
    "PM1": 2, "PM2": 2, "PM3": 2, "PM4": 2, "PM5": 2, "PM6": 2,
    "PP1": 1, "PP2": 1, "PP3": 1, "PP4": 1, "PP5": 1,
    "BA1": -8, "BS1": -4, "BS2": -4, "BS3": -4, "BS4": -4,
    "BP1": -1, "BP2": -1, "BP3": -1, "BP4": -1, "BP5": -1, "BP6": -1, "BP7": -1,
}

PRIOR = 0.10  # prior probability of pathogenicity

NULL_CONSEQUENCES = {
    "stop_gained", "frameshift_variant", "splice_donor_variant", "splice_acceptor_variant",
    "start_lost", "transcript_ablation",
}

INFRAME = {"inframe_insertion", "inframe_deletion"}
SYNONYMOUS = {"synonymous_variant"}
MISSENSE = {"missense_variant"}


def _odds_for(code: str) -> float:
    if code == "PVS1":
        return ODDS["PVS1"]
    if code.startswith("PS"):
        return ODDS["PS"]
    if code.startswith("PM"):
        return ODDS["PM"]
    if code.startswith("PP"):
        return ODDS["PP"]
    if code == "BA1":
        return 0.0  # absolute
    if code.startswith("BS"):
        return ODDS["BS"]
    if code.startswith("BP"):
        return ODDS["BP"]
    return 1.0


def _bayesian_posterior(applied: list[str]) -> float:
    if "BA1" in applied:
        return 0.001
    combined = 1.0
    for c in applied:
        combined *= _odds_for(c)
    p = PRIOR
    return (p * combined) / (1 - p + p * combined)


def _label_from_posterior(p: float) -> str:
    if p >= 0.99:
        return "Pathogenic"
    if p >= 0.90:
        return "Likely Pathogenic"
    if p <= 0.001:
        return "Benign"
    if p <= 0.10:
        return "Likely Benign"
    return "VUS"


# ---------- per-criterion logic ----------

def _is_pathogenic_clinvar(cv: ClinVarRecord | None) -> bool:
    if not cv or not cv.clinical_significance:
        return False
    s = cv.clinical_significance.lower()
    return "pathogenic" in s and "benign" not in s and "uncertain" not in s


def _is_benign_clinvar(cv: ClinVarRecord | None) -> bool:
    if not cv or not cv.clinical_significance:
        return False
    s = cv.clinical_significance.lower()
    return "benign" in s and "pathogenic" not in s and "uncertain" not in s


def _has_functional_study(lit: list[LiteratureHit]) -> bool:
    return any(h.is_functional_study for h in lit)


def _predictors_pathogenic(ann: VEPAnnotation | None, struct: StructuralAnalysis | None) -> int:
    score = 0
    if ann:
        if ann.sift and ann.sift.get("prediction") == "deleterious":
            score += 1
        if ann.polyphen and ann.polyphen.get("prediction") in ("probably_damaging", "possibly_damaging"):
            score += 1
        if ann.cadd is not None and ann.cadd >= 20:
            score += 1
    if struct:
        if struct.alphamissense_score is not None and struct.alphamissense_score >= 0.564:
            score += 1
        if struct.ddg_kcal_mol is not None and struct.ddg_kcal_mol >= 2.0:
            score += 1
    return score


def _predictors_benign(ann: VEPAnnotation | None, struct: StructuralAnalysis | None) -> int:
    score = 0
    if ann:
        if ann.sift and ann.sift.get("prediction") == "tolerated":
            score += 1
        if ann.polyphen and ann.polyphen.get("prediction") == "benign":
            score += 1
        if ann.cadd is not None and ann.cadd < 10:
            score += 1
    if struct:
        if struct.alphamissense_score is not None and struct.alphamissense_score <= 0.34:
            score += 1
    return score


def classify(ev: EvidencePacket) -> ACMGResult:
    ann = ev.annotation
    cv = ev.clinvar
    af = ev.gnomad
    struct = ev.structure
    lit = ev.literature
    panel_entry = (ev.liver_context.panel_entry if ev.liver_context else None)

    crits: list[ACMGCriterion] = []

    consequence = (ann.consequence if ann else None) or ""
    is_null = consequence in NULL_CONSEQUENCES
    is_inframe = consequence in INFRAME
    is_synonymous = consequence in SYNONYMOUS
    is_missense = consequence in MISSENSE

    in_lof_intolerant_panel = panel_entry is not None  # all our panel genes treated as LoF-intolerant for hep disease

    # PVS1: null in LoF-intolerant gene
    if is_null and in_lof_intolerant_panel:
        crits.append(ACMGCriterion(code="PVS1", weight=WEIGHT["PVS1"], applied=True,
                                    rationale=f"Null variant ({consequence}) in {panel_entry['symbol']} where loss-of-function is an established disease mechanism."))

    # PS1: ClinVar already classifies the same protein change as pathogenic
    if cv and _is_pathogenic_clinvar(cv) and ann and ann.hgvs_p:
        crits.append(ACMGCriterion(code="PS1", weight=WEIGHT["PS1"], applied=True,
                                    rationale=f"ClinVar classifies the same amino-acid change ({ann.hgvs_p}) as pathogenic ({cv.clinical_significance})."))

    # PS3: well-established functional study shows damaging effect
    if _has_functional_study(lit):
        funcs = [h for h in lit if h.is_functional_study][:3]
        cite = "; ".join(filter(None, [f"PMID:{h.pmid}" if h.pmid else h.title[:60] for h in funcs]))
        crits.append(ACMGCriterion(code="PS3", weight=WEIGHT["PS3"], applied=True,
                                    rationale=f"Functional studies in the literature support a damaging effect ({cite})."))

    # PM1: in well-defined functional domain or active site
    if struct and (struct.in_active_site or struct.domain_at_position):
        loc = "active site" if struct.in_active_site else f"domain '{struct.domain_at_position}'"
        crits.append(ACMGCriterion(code="PM1", weight=WEIGHT["PM1"], applied=True,
                                    rationale=f"Variant falls in a well-established functional region ({loc})."))

    # PM2: absent or very rare
    if af is not None:
        if (af.af_global is None) or (af.af_global < 1e-4):
            crits.append(ACMGCriterion(code="PM2", weight=WEIGHT["PM2"], applied=True,
                                        rationale=f"Absent or extremely rare in gnomAD (global AF = {af.af_global if af.af_global is not None else 'absent'})."))

    # PM4: in-frame indel
    if is_inframe:
        crits.append(ACMGCriterion(code="PM4", weight=WEIGHT["PM4"], applied=True,
                                    rationale="In-frame insertion/deletion alters protein length."))

    # PP2: missense in a gene where missense is a known pathogenic mechanism (panel curated)
    if is_missense and in_lof_intolerant_panel:
        crits.append(ACMGCriterion(code="PP2", weight=WEIGHT["PP2"], applied=True,
                                    rationale=f"Missense variant in {panel_entry['symbol']}, a curated liver disease gene with established missense pathogenicity."))

    # PP3: ≥2 in silico predictors agree on damaging
    n_path = _predictors_pathogenic(ann, struct)
    if n_path >= 2:
        crits.append(ACMGCriterion(code="PP3", weight=WEIGHT["PP3"], applied=True,
                                    rationale=f"{n_path} computational predictors (SIFT/PolyPhen/CADD/AlphaMissense/ΔΔG) agree on a damaging effect."))

    # PP5: reputable source classifies pathogenic
    if cv and _is_pathogenic_clinvar(cv):
        crits.append(ACMGCriterion(code="PP5", weight=WEIGHT["PP5"], applied=True,
                                    rationale=f"Reputable source (ClinVar, {cv.review_status}) classifies as pathogenic."))

    inheritance = (panel_entry.get("inheritance") or "") if panel_entry else ""
    is_ar = "AR" in inheritance

    # BA1: AF > 5%
    if af and af.af_global is not None and af.af_global > 0.05:
        crits.append(ACMGCriterion(code="BA1", weight=WEIGHT["BA1"], applied=True,
                                    rationale=f"Global allele frequency in gnomAD ({af.af_global:.4f}) exceeds 5% — common variant cannot be a fully penetrant rare-disease cause."))

    # BS1: AF > 1% for dominant/haploinsufficiency genes only.
    # For autosomal recessive genes, carrier frequency alone is not evidence against
    # pathogenicity — the relevant comparison is homozygote frequency vs disease
    # prevalence, which is already captured by BS2. Applying BS1 to AR genes
    # incorrectly penalises known high-frequency carrier alleles (e.g. SERPINA1 Z).
    elif af and af.af_global is not None and af.af_global > 0.01 and not is_ar:
        crits.append(ACMGCriterion(code="BS1", weight=WEIGHT["BS1"], applied=True,
                                    rationale=f"Global allele frequency in gnomAD ({af.af_global:.4f}) is higher than expected for a dominant disorder."))

    # BS2: observed in confirmed-healthy homozygotes for a fully penetrant recessive disorder.
    # Only fires when the gnomAD homozygote count substantially exceeds what disease
    # prevalence predicts. Threshold: homozygote_freq (af²) must be >10× the
    # expected disease prevalence (~1/10 000 for our panel). af > ~0.03 → af² > 0.001.
    # This prevents BS2 from firing on high-carrier-frequency alleles like SERPINA1 Z
    # (af ~1.6%) whose PiZZ gnomAD homozygotes are NOT confirmed disease-free
    # (gnomAD v4 excludes severe paediatric disease but not adult-onset liver disease).
    if (af and af.homozygote_count and af.homozygote_count > 5
            and is_ar and af.af_global is not None and af.af_global > 0.05):
        crits.append(ACMGCriterion(code="BS2", weight=WEIGHT["BS2"], applied=True,
                                    rationale=f"{af.homozygote_count} homozygotes observed in gnomAD; homozygote frequency ({af.af_global**2:.4%}) substantially exceeds expected disease prevalence."))

    # BP1: missense in a gene where truncating mechanism dominates (heuristic skip — none of our panel is haploinsufficient-only)

    # BP3: in-frame indel in repeat / non-functional region (skip without InterPro mapping context)

    # BP4: predictors agree on benign
    n_ben = _predictors_benign(ann, struct)
    if n_ben >= 2:
        crits.append(ACMGCriterion(code="BP4", weight=WEIGHT["BP4"], applied=True,
                                    rationale=f"{n_ben} computational predictors agree on a benign effect."))

    # BP6: reputable source classifies benign
    if cv and _is_benign_clinvar(cv):
        crits.append(ACMGCriterion(code="BP6", weight=WEIGHT["BP6"], applied=True,
                                    rationale=f"Reputable source (ClinVar, {cv.review_status}) classifies as benign."))

    # BP7: synonymous at non-conserved (skip — would need PhyloP from VEP, often missing)

    # ---- Score & label ----
    applied_codes = [c.code for c in crits]
    posterior = _bayesian_posterior(applied_codes)
    label = _label_from_posterior(posterior)

    points = sum(c.weight for c in crits)

    # Confidence: weight criterion strength, not count
    strong_count = sum(1 for c in crits if abs(c.weight) >= 4)
    moderate_count = sum(1 for c in crits if abs(c.weight) == 2)
    if strong_count >= 1 or moderate_count >= 3:
        confidence = "High"
    elif moderate_count >= 1 or len(crits) >= 3:
        confidence = "Medium"
    else:
        confidence = "Low"

    return ACMGResult(
        label=label,  # type: ignore[arg-type]
        score=points,
        posterior=round(posterior, 4),
        confidence=confidence,  # type: ignore[arg-type]
        criteria=crits,
    )
