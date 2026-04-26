"""Unit tests for the ACMG/AMP Tavtigian Bayesian classifier."""
from __future__ import annotations

from backend.pipeline.acmg import classify
from shared.schemas import (
    ClinVarRecord,
    EvidencePacket,
    GnomadFreq,
    LiverContext,
    StructuralAnalysis,
    VariantInput,
    VEPAnnotation,
)


VARIANT = VariantInput(chrom="chr7", pos=87408188, ref="T", alt="C", assembly="GRCh38")


def _packet(**kwargs) -> EvidencePacket:
    base = dict(variant=VARIANT)
    base.update(kwargs)
    return EvidencePacket(**base)


def test_pvs1_null_in_panel_gene_is_likely_pathogenic_or_better():
    ev = _packet(
        annotation=VEPAnnotation(gene_symbol="ABCB4", consequence="frameshift_variant"),
        gnomad=GnomadFreq(af_global=None, has_amr=False),
        liver_context=LiverContext(in_panel=True, panel_entry={"symbol": "ABCB4", "inheritance": "AR"}),
    )
    res = classify(ev)
    assert res.label in ("Pathogenic", "Likely Pathogenic")
    assert any(c.code == "PVS1" for c in res.criteria)
    assert any(c.code == "PM2" for c in res.criteria)
    assert res.score >= 8


def test_ba1_overrides_to_benign():
    ev = _packet(
        annotation=VEPAnnotation(gene_symbol="ABCB4", consequence="missense_variant"),
        gnomad=GnomadFreq(af_global=0.07, has_amr=True),
        liver_context=LiverContext(in_panel=True, panel_entry={"symbol": "ABCB4", "inheritance": "AR"}),
    )
    res = classify(ev)
    assert res.label == "Benign"
    assert any(c.code == "BA1" for c in res.criteria)


def test_pp3_when_two_predictors_damaging():
    ev = _packet(
        annotation=VEPAnnotation(
            gene_symbol="ABCB4",
            consequence="missense_variant",
            sift={"prediction": "deleterious", "score": 0.0},
            polyphen={"prediction": "probably_damaging", "score": 0.99},
            cadd=28.0,
        ),
        structure=StructuralAnalysis(alphamissense_score=0.85, alphamissense_class="likely_pathogenic", ddg_kcal_mol=3.2),
        gnomad=GnomadFreq(af_global=None, has_amr=False),
        liver_context=LiverContext(in_panel=True, panel_entry={"symbol": "ABCB4", "inheritance": "AR"}),
    )
    res = classify(ev)
    assert any(c.code == "PP3" for c in res.criteria)
    assert any(c.code == "PM2" for c in res.criteria)
    assert any(c.code == "PP2" for c in res.criteria)


def test_clinvar_pathogenic_applies_pp5_and_ps1():
    ev = _packet(
        annotation=VEPAnnotation(gene_symbol="ATP7B", hgvs_p="p.His1069Gln", consequence="missense_variant"),
        clinvar=ClinVarRecord(clinical_significance="Pathogenic", review_status="reviewed by expert panel"),
        gnomad=GnomadFreq(af_global=1e-5, has_amr=False),
        liver_context=LiverContext(in_panel=True, panel_entry={"symbol": "ATP7B", "inheritance": "AR"}),
    )
    res = classify(ev)
    codes = {c.code for c in res.criteria}
    assert "PS1" in codes
    assert "PP5" in codes


def test_empty_evidence_is_vus():
    ev = _packet(
        annotation=VEPAnnotation(gene_symbol="ABCB4", consequence="missense_variant"),
        gnomad=GnomadFreq(af_global=0.005, has_amr=True),
        liver_context=LiverContext(in_panel=True, panel_entry={"symbol": "ABCB4", "inheritance": "AR"}),
    )
    res = classify(ev)
    # AF 0.005 is below BS1 threshold (0.01) so PM2 may not apply, no benign criteria; only PP2
    assert res.label in ("VUS", "Likely Benign")
