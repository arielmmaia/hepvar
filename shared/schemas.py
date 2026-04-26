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


class AAProperty(BaseModel):
    code: str   # 1-letter
    three: str  # 3-letter
    name: str
    mw: float | None = None
    volume: float | None = None
    hydrophobicity: float | None = None
    charge: int | None = None
    polar: bool | None = None
    aromatic: bool | None = None
    sulfur: bool | None = None
    side_chain: str | None = None
    h_bond: str | None = None
    features: list[str] = Field(default_factory=list)


class AASubstitution(BaseModel):
    """Side-by-side comparison of WT vs variant amino-acid properties."""
    wild_type: AAProperty
    variant: AAProperty
    delta_volume: float | None = None
    delta_hydrophobicity: float | None = None
    delta_charge: int | None = None
    summary_flags: list[str] = Field(default_factory=list)  # human-readable change descriptors


class TranscriptConsequence(BaseModel):
    transcript_id: str | None = None
    transcript_biotype: str | None = None
    gene_symbol: str | None = None
    canonical: bool = False
    mane_select: str | None = None
    refseq_match: str | None = None  # NM_ accession when present
    hgvs_c: str | None = None
    hgvs_p: str | None = None
    consequence: str | None = None
    impact: str | None = None
    aa_position: int | None = None
    aa_ref: str | None = None  # 1-letter
    aa_alt: str | None = None  # 1-letter


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
    aa_substitution: AASubstitution | None = None
    transcripts: list[TranscriptConsequence] = Field(default_factory=list)
    # Strand of the canonical transcript on the reference genome.
    # 1 = sense (+); -1 = antisense (−). Antisense genes need a strand
    # explainer because genomic ref/alt is reverse-complemented vs HGVS.c.
    gene_strand: int | None = None
    genomic_ref: str | None = None  # the literal ref base on + strand
    genomic_alt: str | None = None  # the literal alt base on + strand
    coding_ref: str | None = None   # base on the transcript strand (== genomic for + strand)
    coding_alt: str | None = None


class LiftoverInfo(BaseModel):
    """Cross-assembly liftover + the wrong-assembly disambiguation trap."""
    source_assembly: str | None = None  # what the user gave us
    source_pos: int | None = None
    target_assembly: str | None = None  # the *other* build
    target_pos: int | None = None
    target_chrom: str | None = None
    # Gene that overlaps the *input pos number* if it were (mis-)interpreted as
    # the other assembly. If this differs from the actual gene, we warn.
    wrong_assembly_gene: str | None = None
    ambiguity_warning: bool = False


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
    variant_residue_plddt: float | None = None
    variant_residue_plddt_band: str | None = None  # "very high" | "confident" | "low" | "very low"
    variant_pdb_url: str | None = None
    variant_method: Literal["esmfold", "alphafold", "none"] = "none"
    rmsd_angstrom: float | None = None
    alphamissense_score: float | None = None
    alphamissense_class: str | None = None
    ddg_kcal_mol: float | None = None
    domain_at_position: str | None = None
    in_active_site: bool = False
    solvent_accessibility: float | None = None


class SequenceAnnotation(BaseModel):
    position: int             # absolute residue number on the protein
    relative: int             # offset from the variant residue (negative = upstream)
    kind: str                 # "variant" | "active_site" | "binding_site" | "domain_start" | "domain_end" | "motif" | "modified"
    label: str | None = None  # human-readable description


class OrthologResidue(BaseModel):
    species: str                 # binomial name (e.g. mus_musculus)
    common_name: str | None = None
    residue: str | None = None   # 1-letter at the variant-equivalent alignment position
    is_gap: bool = False
    matches_human: bool = False  # residue == human ref residue
    perc_id: float | None = None # overall ortholog protein identity vs human


class ConservationPanel(BaseModel):
    gene_symbol: str | None = None
    variant_position: int | None = None
    human_residue: str | None = None
    n_orthologs: int = 0
    n_match: int = 0
    pct_conserved_at_position: float | None = None  # 0-100; orthologs identical at this position
    species: list[OrthologResidue] = Field(default_factory=list)


class SequenceContext(BaseModel):
    """A ±N residue strip around the variant for visual display."""
    accession: str | None = None
    start: int | None = None              # 1-based start of the displayed strip
    end: int | None = None                # 1-based end (inclusive)
    sequence: str | None = None           # the slice itself (uppercase)
    variant_position: int | None = None   # absolute residue number of the variant
    variant_offset: int | None = None     # 0-based index within `sequence`
    variant_ref: str | None = None        # 1-letter
    variant_alt: str | None = None        # 1-letter
    annotations: list[SequenceAnnotation] = Field(default_factory=list)


class AlphaGenomeTrack(BaseModel):
    name: str | None = None              # human-readable track label
    biosample: str | None = None         # tissue / cell line
    max_abs_delta: float | None = None
    sum_abs_delta: float | None = None


class AlphaGenomeModality(BaseModel):
    output_type: str                       # rna_seq | splice_sites | atac | cage | …
    n_tracks: int = 0
    max_abs_delta: float | None = None
    sum_abs_delta: float | None = None
    sparkline: list[float] = Field(default_factory=list)  # mean Δ across tracks, length ≤64
    sparkline_window: int | None = None    # half-window in bp around variant
    tracks: list[AlphaGenomeTrack] = Field(default_factory=list)


class AlphaGenomePrediction(BaseModel):
    splice_delta: float | None = None
    expression_log2fc: float | None = None
    chromatin_accessibility_delta: float | None = None
    tf_binding_delta: float | None = None
    liver_tracks_used: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    modalities: list[AlphaGenomeModality] = Field(default_factory=list)


class DiseaseEntity(BaseModel):
    name: str
    abbrev: str | None = None
    inheritance: str | None = None
    residual_activity: str | None = None
    age_onset: str | None = None
    ggt: str | None = None
    features: list[str] = Field(default_factory=list)


class LiverContext(BaseModel):
    in_panel: bool = False
    panel_entry: dict[str, Any] | None = None
    gtex_liver_tpm: float | None = None
    hpa_liver_expression: str | None = None
    reactome_pathways: list[str] = Field(default_factory=list)
    kegg_pathways: list[str] = Field(default_factory=list)
    disease_spectrum: list[DiseaseEntity] = Field(default_factory=list)


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
    liftover: LiftoverInfo | None = None
    gnomad: GnomadFreq | None = None
    clinvar: ClinVarRecord | None = None
    uniprot: dict[str, Any] | None = None
    interpro: dict[str, Any] | None = None
    literature: list[LiteratureHit] = Field(default_factory=list)
    alphagenome: AlphaGenomePrediction | None = None
    structure: StructuralAnalysis | None = None
    sequence_context: SequenceContext | None = None
    conservation: ConservationPanel | None = None
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
