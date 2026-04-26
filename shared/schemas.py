"""Source-of-truth Pydantic schemas shared between backend pipeline, reasoning layer, and frontend.

Frontend mirrors these as TypeScript types in `frontend/lib/types.ts`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


Confidence = Literal["high", "partial", "missing"]
ACMGLabel = Literal["Pathogenic", "Likely Pathogenic", "VUS", "Likely Benign", "Benign"]
EvidenceStatus = Literal["pending", "running", "ok", "partial", "missing", "error"]


class VariantInput(BaseModel):
    chrom: str
    pos: int
    ref: str
    alt: str
    assembly: Literal["GRCh38", "GRCh37"] = "GRCh38"


class SourceResult(BaseModel):
    """One pipeline source's payload + provenance."""
    name: str
    status: EvidenceStatus = "pending"
    confidence: Confidence = "missing"
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    elapsed_ms: int | None = None


class VEPAnnotation(BaseModel):
    gene_symbol: str | None = None
    transcript_id: str | None = None
    hgvs_c: str | None = None
    hgvs_p: str | None = None
    consequence: str | None = None
    impact: str | None = None
    rs_id: str | None = None
    clinvar_id: str | None = None
    uniprot_accession: str | None = None
    sift: dict[str, Any] | None = None
    polyphen: dict[str, Any] | None = None
    cadd: float | None = None
    aa_change: dict[str, Any] | None = None  # {ref, alt, position, ref1letter, alt1letter}


class GnomadFreq(BaseModel):
    af_global: float | None = None
    af_populations: dict[str, float] = Field(default_factory=dict)
    homozygote_count: int | None = None
    hemizygote_count: int | None = None
    flags: list[str] = Field(default_factory=list)
    has_amr: bool = False
    notes: str | None = None


class ClinVarRecord(BaseModel):
    clinical_significance: str | None = None
    review_status: str | None = None
    star_rating: int | None = None
    conditions: list[str] = Field(default_factory=list)
    last_evaluated: str | None = None
    accession: str | None = None


class LiteratureHit(BaseModel):
    pmid: str | None = None
    doi: str | None = None
    title: str
    journal: str | None = None
    year: int | None = None
    abstract: str | None = None
    language: str = "en"
    relevance_score: float = 0.0
    matched_aliases: list[str] = Field(default_factory=list)
    is_case_report: bool = False
    is_functional_study: bool = False


class StructuralAnalysis(BaseModel):
    uniprot_accession: str | None = None
    af_pdb_url: str | None = None
    af_mean_plddt: float | None = None
    variant_pdb_url: str | None = None
    variant_method: Literal["esmfold", "alphafold", "none"] = "none"
    rmsd_angstrom: float | None = None
    alphamissense_score: float | None = None
    alphamissense_class: str | None = None
    ddg_kcal_mol: float | None = None
    domain_at_position: str | None = None
    in_active_site: bool = False
    solvent_accessibility: float | None = None


class AlphaGenomePrediction(BaseModel):
    splice_delta: float | None = None
    expression_log2fc: float | None = None
    chromatin_accessibility_delta: float | None = None
    tf_binding_delta: float | None = None
    liver_tracks_used: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class LiverContext(BaseModel):
    in_panel: bool = False
    panel_entry: dict[str, Any] | None = None
    gtex_liver_tpm: float | None = None
    hpa_liver_expression: str | None = None
    reactome_pathways: list[str] = Field(default_factory=list)
    kegg_pathways: list[str] = Field(default_factory=list)


class ACMGCriterion(BaseModel):
    code: str  # PVS1, PS1, ..., BP7
    weight: int  # Tavtigian Bayesian point weight
    applied: bool
    rationale: str | None = None


class ACMGResult(BaseModel):
    label: ACMGLabel
    score: int
    posterior: float | None = None
    confidence: Literal["High", "Medium", "Low"] = "Low"
    criteria: list[ACMGCriterion] = Field(default_factory=list)


class EvidencePacket(BaseModel):
    """Complete evidence object handed to Opus 4.7 for synthesis."""
    variant: VariantInput
    annotation: VEPAnnotation | None = None
    gnomad: GnomadFreq | None = None
    clinvar: ClinVarRecord | None = None
    uniprot: dict[str, Any] | None = None
    interpro: dict[str, Any] | None = None
    lovd: dict[str, Any] | None = None
    literature: list[LiteratureHit] = Field(default_factory=list)
    alphagenome: AlphaGenomePrediction | None = None
    structure: StructuralAnalysis | None = None
    liver_context: LiverContext | None = None
    acmg: ACMGResult | None = None
    sources: list[SourceResult] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class SynthesisSection(BaseModel):
    verdict: str | None = None
    evidence_synthesis: str | None = None
    conflict_resolution: str | None = None
    evidence_gaps: str | None = None
    clinical_recommendation: str | None = None


class Report(BaseModel):
    job_id: str
    variant: VariantInput
    evidence: EvidencePacket
    synthesis: SynthesisSection | None = None
    raw_synthesis_markdown: str | None = None
    thinking_log: str | None = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class StepEvent(BaseModel):
    type: Literal["step", "reasoning_delta", "thinking_delta", "synthesis_section", "done", "error"]
    name: str | None = None
    status: EvidenceStatus | None = None
    data: dict[str, Any] | None = None
    text: str | None = None
    section: str | None = None
