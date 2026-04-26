// TypeScript mirror of backend/shared/schemas.py (manually kept in sync — small surface).

export type ACMGLabel = "Pathogenic" | "Likely Pathogenic" | "VUS" | "Likely Benign" | "Benign";
export type EvidenceStatus = "pending" | "running" | "ok" | "partial" | "missing" | "error";

export interface VariantInput {
  chrom: string;
  pos: number;
  ref: string;
  alt: string;
  assembly?: "GRCh38" | "GRCh37";
}

export interface AAProperty {
  code: string;
  three: string;
  name: string;
  mw?: number | null;
  volume?: number | null;
  hydrophobicity?: number | null;
  charge?: number | null;
  polar?: boolean | null;
  aromatic?: boolean | null;
  sulfur?: boolean | null;
  side_chain?: string | null;
  h_bond?: string | null;
  features?: string[];
}

export interface AASubstitution {
  wild_type: AAProperty;
  variant: AAProperty;
  delta_volume?: number | null;
  delta_hydrophobicity?: number | null;
  delta_charge?: number | null;
  summary_flags?: string[];
}

export interface VEPAnnotation {
  gene_symbol?: string | null;
  transcript_id?: string | null;
  hgvs_c?: string | null;
  hgvs_p?: string | null;
  consequence?: string | null;
  impact?: string | null;
  rs_id?: string | null;
  clinvar_id?: string | null;
  uniprot_accession?: string | null;
  sift?: { score?: number | null; prediction?: string | null } | null;
  polyphen?: { score?: number | null; prediction?: string | null } | null;
  cadd?: number | null;
  aa_change?: { ref: string; alt: string; position: number; ref1letter: string; alt1letter: string } | null;
  aa_substitution?: AASubstitution | null;
}

export interface GnomadFreq {
  af_global?: number | null;
  af_populations?: Record<string, number>;
  homozygote_count?: number | null;
  hemizygote_count?: number | null;
  flags?: string[];
  has_amr?: boolean;
  notes?: string | null;
}

export interface ClinVarRecord {
  clinical_significance?: string | null;
  review_status?: string | null;
  star_rating?: number | null;
  conditions?: string[];
  last_evaluated?: string | null;
  accession?: string | null;
}

export interface LiteratureHit {
  pmid?: string | null;
  doi?: string | null;
  title: string;
  journal?: string | null;
  year?: number | null;
  abstract?: string | null;
  language: string;
  relevance_score: number;
  matched_aliases?: string[];
  is_case_report?: boolean;
  is_functional_study?: boolean;
}

export interface StructuralAnalysis {
  uniprot_accession?: string | null;
  af_pdb_url?: string | null;
  af_mean_plddt?: number | null;
  variant_pdb_url?: string | null;
  variant_method?: "esmfold" | "alphafold" | "none";
  rmsd_angstrom?: number | null;
  alphamissense_score?: number | null;
  alphamissense_class?: string | null;
  ddg_kcal_mol?: number | null;
  domain_at_position?: string | null;
  in_active_site?: boolean;
  solvent_accessibility?: number | null;
}

export interface AlphaGenomePrediction {
  splice_delta?: number | null;
  expression_log2fc?: number | null;
  chromatin_accessibility_delta?: number | null;
  tf_binding_delta?: number | null;
  liver_tracks_used?: string[];
  flags?: string[];
}

export interface LiverContext {
  in_panel?: boolean;
  panel_entry?: Record<string, unknown> | null;
  gtex_liver_tpm?: number | null;
  hpa_liver_expression?: string | null;
  reactome_pathways?: string[];
  kegg_pathways?: string[];
}

export interface ACMGCriterion {
  code: string;
  weight: number;
  applied: boolean;
  rationale?: string | null;
}

export interface ACMGResult {
  label: ACMGLabel;
  score: number;
  posterior?: number | null;
  confidence?: "High" | "Medium" | "Low";
  criteria: ACMGCriterion[];
}

export interface EvidencePacket {
  variant: VariantInput;
  annotation?: VEPAnnotation | null;
  gnomad?: GnomadFreq | null;
  clinvar?: ClinVarRecord | null;
  uniprot?: Record<string, unknown> | null;
  interpro?: Record<string, unknown> | null;
  lovd?: Record<string, unknown> | null;
  literature?: LiteratureHit[];
  alphagenome?: AlphaGenomePrediction | null;
  structure?: StructuralAnalysis | null;
  liver_context?: LiverContext | null;
  acmg?: ACMGResult | null;
  sources?: { name: string; status: EvidenceStatus; confidence?: string; elapsed_ms?: number; error?: string }[];
}

export interface SynthesisSection {
  verdict?: string | null;
  evidence_synthesis?: string | null;
  conflict_resolution?: string | null;
  evidence_gaps?: string | null;
  clinical_recommendation?: string | null;
}

export interface Report {
  job_id: string;
  variant: VariantInput;
  evidence: EvidencePacket;
  synthesis?: SynthesisSection | null;
  raw_synthesis_markdown?: string | null;
  thinking_log?: string | null;
}

export type StreamEvent =
  | { type: "step"; name: string; status: EvidenceStatus; data?: any; elapsed_ms?: number }
  | { type: "reasoning_delta"; text: string }
  | { type: "thinking_delta"; text: string }
  | { type: "synthesis_section"; section: string; text: string }
  | { type: "done"; data: Report }
  | { type: "error"; text: string };

export type ChatEvent = { type: "chat_delta"; text: string } | { type: "chat_done" };
