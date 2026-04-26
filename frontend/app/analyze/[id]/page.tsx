"use client";
import { use, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { streamJob } from "@/lib/api";
import type { EvidencePacket, EvidenceStatus, Report, StreamEvent, VEPAnnotation, GnomadFreq, ClinVarRecord, LiteratureHit, AlphaGenomePrediction, StructuralAnalysis, LiverContext, ACMGResult } from "@/lib/types";
import { EvidenceCard } from "@/components/EvidenceCard";
import { VerdictCard } from "@/components/VerdictCard";
import { AcmgChecklist } from "@/components/AcmgChecklist";
import { ReasoningPane } from "@/components/ReasoningPane";
import { ChatComposer } from "@/components/ChatComposer";
import { StructureViewer } from "@/components/StructureViewer";
import { LiteratureList } from "@/components/LiteratureList";
import { StatusDot } from "@/components/StatusDot";
import { AASubstitutionCard } from "@/components/AASubstitutionCard";
import { TranscriptTable } from "@/components/TranscriptTable";
import { StrandExplainer } from "@/components/StrandExplainer";
import { LiftoverNote } from "@/components/LiftoverNote";
import { PopulationBarChart } from "@/components/PopulationBarChart";
import { DiseaseSpectrumTable } from "@/components/DiseaseSpectrumTable";
import { SequenceContextStrip } from "@/components/SequenceContextStrip";
import { AlphaGenomePanel } from "@/components/AlphaGenomePanel";

const STEP_ORDER = [
  "annotate", "liftover", "liver_context", "gnomad", "clinvar", "uniprot", "interpro",
  "literature", "alphagenome", "structure", "sequence_context", "acmg", "synthesis",
];

const STEP_LABEL: Record<string, string> = {
  annotate: "VEP", liftover: "lift", liver_context: "liver", gnomad: "gnomAD", clinvar: "ClinVar",
  uniprot: "UniProt", interpro: "InterPro", literature: "literature",
  alphagenome: "AlphaGenome", structure: "structure", sequence_context: "context",
  acmg: "ACMG", synthesis: "Opus 4.7",
};

interface StepState { status: EvidenceStatus; data?: any; elapsedMs?: number }

export default function AnalyzePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [steps, setSteps] = useState<Record<string, StepState>>({});
  const [reasoning, setReasoning] = useState("");
  const [thinking, setThinking] = useState("");
  const [report, setReport] = useState<Report | null>(null);

  // refs to avoid stale closures
  const reasoningBuf = useRef("");
  const thinkingBuf = useRef("");

  useEffect(() => {
    // Reset only when the job id actually changes — not on every effect run —
    // because the backend resumes via Last-Event-ID on reconnect, so any
    // re-mount that opens a fresh EventSource will pick up *after* the events
    // we've already processed and not replay the synthesis from scratch.
    reasoningBuf.current = "";
    thinkingBuf.current = "";
    setSteps({});
    setReasoning("");
    setThinking("");
    setReport(null);

    const close = streamJob(id, (ev: StreamEvent) => {
      if (ev.type === "step") {
        setSteps((s) => ({ ...s, [ev.name]: { status: ev.status, data: (ev as any).data, elapsedMs: (ev as any).elapsed_ms } }));
      } else if (ev.type === "reasoning_delta") {
        reasoningBuf.current += ev.text;
        setReasoning(reasoningBuf.current);
      } else if (ev.type === "thinking_delta") {
        thinkingBuf.current += ev.text;
        setThinking(thinkingBuf.current);
      } else if (ev.type === "done") {
        setReport(ev.data);
      }
    });
    return close;
  }, [id]);

  const ann: VEPAnnotation | undefined = steps.annotate?.data;
  const liftover = steps.liftover?.data as import("@/lib/types").LiftoverInfo | undefined;
  const gnomad: GnomadFreq | undefined = steps.gnomad?.data;
  const clinvar: ClinVarRecord | undefined = steps.clinvar?.data;
  const uniprot: any = steps.uniprot?.data;
  const interpro: any = steps.interpro?.data;

  const literature: LiteratureHit[] = useMemo(() => {
    const d = steps.literature?.data;
    if (!d) return [];
    if (Array.isArray(d)) return d;
    if (d.items) return d.items;
    return [];
  }, [steps.literature]);
  const alphagenome: AlphaGenomePrediction | undefined = steps.alphagenome?.data;
  const structure: StructuralAnalysis | undefined = steps.structure?.data;
  const liver: LiverContext | undefined = steps.liver_context?.data;
  const acmg: ACMGResult | undefined = steps.acmg?.data;
  const seqctx = steps.sequence_context?.data as import("@/lib/types").SequenceContext | undefined;


  const variantStr = report?.variant
    ? `${report.variant.chrom}:${report.variant.pos} ${report.variant.ref}>${report.variant.alt}`
    : "";

  return (
    <main className="max-w-[1380px] mx-auto px-5 md:px-8 py-6">
      {/* Header */}
      <header className="flex items-center justify-between mb-6">
        <Link href="/" className="font-display text-xl font-semibold text-oxblood">HepVar</Link>
        <ul className="hidden md:flex items-center gap-3 text-[11px] font-mono uppercase tracking-[0.18em] text-muted">
          {STEP_ORDER.map((s) => (
            <li key={s} className="flex items-center gap-1.5">
              <StatusDot status={steps[s]?.status ?? "pending"} />
              <span>{STEP_LABEL[s]}</span>
            </li>
          ))}
        </ul>
      </header>

      {/* Variant strip */}
      <motion.section
        initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}
        className="rounded-3xl bg-ink text-surface px-7 py-5 mb-6 flex items-center justify-between flex-wrap gap-4"
      >
        <div>
          <p className="text-[10px] uppercase tracking-[0.3em] text-amber font-mono opacity-90">Variant under interpretation</p>
          <h1 className="font-display text-[36px] tracking-tightest font-light">
            <span className="font-mono">{variantStr || "loading…"}</span>
            {ann?.gene_symbol && <span className="serif-italic text-amber"> · {ann.gene_symbol}</span>}
          </h1>
          {ann && (
            <p className="text-[13px] text-surface/70 font-mono mt-1">
              {ann.hgvs_c} · {ann.hgvs_p} · {ann.consequence} · {ann.transcript_id}
            </p>
          )}
        </div>
        {liver?.panel_entry && (
          <div className="text-right max-w-[36ch]">
            <p className="text-[10px] uppercase tracking-[0.3em] text-amber/90 font-mono">Liver disease panel</p>
            <p className="font-display text-[18px]">{(liver.panel_entry as any).diseases?.join(" · ")}</p>
            <p className="text-[12px] text-surface/70 italic serif-italic">{(liver.panel_entry as any).pathway}</p>
          </div>
        )}
      </motion.section>

      <div className="grid lg:grid-cols-12 gap-6">
        {/* Evidence column */}
        <section className="lg:col-span-7 space-y-4">
          <h2 className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted mb-2">Assembled evidence</h2>

          {ann?.gene_strand === -1 && report && (
            <StrandExplainer ann={ann} variant={report.variant} />
          )}

          {liftover && <LiftoverNote info={liftover} geneSymbol={ann?.gene_symbol} />}

          <AnimatePresence>
            {ann?.aa_substitution && (
              <EvidenceCard key="aa_sub" eyebrow="amino-acid substitution" title={`${ann.aa_substitution.wild_type.three}${ann.aa_change?.position} → ${ann.aa_substitution.variant.three}`} status="ok" accent="teal">
                <AASubstitutionCard sub={ann.aa_substitution} />
              </EvidenceCard>
            )}

            {ann?.transcripts && ann.transcripts.length > 1 && (
              <EvidenceCard key="transcripts" eyebrow="isoforms · all transcripts" title={`${ann.transcripts.length} transcripts annotated`} status="ok" accent="amber">
                <TranscriptTable transcripts={ann.transcripts} />
              </EvidenceCard>
            )}

            {ann && (
              <EvidenceCard key="vep" eyebrow="annotation · VEP" title="Variant annotation" status={steps.annotate.status} elapsedMs={steps.annotate.elapsedMs} accent="oxblood">
                <KV k="gene" v={ann.gene_symbol} />
                <KV k="HGVS.c" v={ann.hgvs_c} mono />
                <KV k="HGVS.p" v={ann.hgvs_p} mono />
                <KV k="consequence" v={ann.consequence} />
                <KV k="impact" v={ann.impact} />
                <KV k="rsID" v={ann.rs_id} mono />
                <KV k="UniProt" v={ann.uniprot_accession} mono />
                <div className="mt-2 grid grid-cols-3 gap-1 text-[12px] text-muted font-mono">
                  <Pred label="SIFT" pred={ann.sift?.prediction} score={ann.sift?.score} />
                  <Pred label="PolyPhen" pred={ann.polyphen?.prediction} score={ann.polyphen?.score} />
                  <Pred label="CADD" pred={null} score={ann.cadd ?? null} />
                </div>
              </EvidenceCard>
            )}

            {gnomad && (
              <EvidenceCard key="gn" eyebrow="population · gnomAD v4" title="Allele frequency" status={steps.gnomad.status} elapsedMs={steps.gnomad.elapsedMs} accent="amber">
                <div className="flex items-baseline gap-3 mb-3">
                  <span className="font-mono text-[26px] font-display tracking-tight text-ink">
                    {gnomad.af_global !== null && gnomad.af_global !== undefined ? gnomad.af_global.toExponential(2) : "absent"}
                  </span>
                  <span className="text-[12px] text-muted">global · {gnomad.homozygote_count ?? 0} homozygotes</span>
                </div>
                {gnomad.af_populations && Object.keys(gnomad.af_populations).length > 0 ? (
                  <PopulationBarChart gnomad={gnomad} />
                ) : (
                  <p className="text-[12px] text-muted italic serif-italic">No per-ancestry breakdown returned.</p>
                )}
              </EvidenceCard>
            )}

            {clinvar && (
              <EvidenceCard key="cv" eyebrow="clinical · ClinVar" title={clinvar.clinical_significance ?? "no submission"} status={steps.clinvar.status} elapsedMs={steps.clinvar.elapsedMs} accent="oxblood">
                {clinvar.review_status && <p className="text-[12px] text-muted">{clinvar.review_status} · {"★".repeat(clinvar.star_rating ?? 0)}</p>}
                {clinvar.conditions && clinvar.conditions.length > 0 && (
                  <ul className="mt-2 text-[13px] list-disc pl-4 text-ink2">
                    {clinvar.conditions.slice(0, 4).map((c) => <li key={c}>{c}</li>)}
                  </ul>
                )}
              </EvidenceCard>
            )}

            {uniprot && uniprot.name && (
              <EvidenceCard key="up" eyebrow="protein · UniProt + InterPro" title={uniprot.name ?? uniprot.accession} status={steps.uniprot.status} elapsedMs={steps.uniprot.elapsedMs} accent="teal">
                {uniprot.function && <p className="italic serif-italic text-ink2 mb-2">{uniprot.function}</p>}
                {uniprot.length && <p className="text-[12px] text-muted font-mono">length {uniprot.length} aa</p>}
                {(uniprot.domains?.length ?? 0) > 0 && (
                  <div className="mt-2">
                    <p className="text-[10px] uppercase tracking-[0.2em] text-muted font-mono">domains</p>
                    <ul className="text-[13px] mt-1 space-y-0.5">
                      {uniprot.domains.slice(0, 4).map((d: any, i: number) => (
                        <li key={i} className="text-ink2"><span className="font-mono text-muted">{d.begin}–{d.end}</span> {d.description}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {interpro?.entries?.length > 0 && (
                  <div className="mt-2 text-[12px] text-muted">InterPro: {interpro.entries.slice(0, 3).map((e: any) => e.name).join(" · ")}</div>
                )}
              </EvidenceCard>
            )}

            {alphagenome && (
              <EvidenceCard key="ag" eyebrow="regulatory · AlphaGenome · liver" title="Liver-cell predictions" status={steps.alphagenome.status} elapsedMs={steps.alphagenome.elapsedMs} accent="teal">
                <AlphaGenomePanel pred={alphagenome} />
              </EvidenceCard>
            )}

            {seqctx && seqctx.sequence && (
              <EvidenceCard key="seqctx" eyebrow="sequence context · UniProt + InterPro" title="Local sequence around the variant" status="ok" accent="teal">
                <SequenceContextStrip ctx={seqctx} />
              </EvidenceCard>
            )}


            {structure && (
              <EvidenceCard key="st" eyebrow="structure · AlphaFold + ESMFold + AlphaMissense" title="Structural impact" status={steps.structure.status} elapsedMs={steps.structure.elapsedMs} accent="oxblood">
                <StructureViewer
                  pdbUrl={structure.af_pdb_url ?? null}
                  position={ann?.aa_change?.position}
                  refAa={ann?.aa_change?.ref1letter}
                  altAa={ann?.aa_change?.alt1letter}
                />
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[13px] mt-3">
                  <Stat label="AlphaMissense" value={structure.alphamissense_score} suffix={structure.alphamissense_class ? ` · ${structure.alphamissense_class}` : ""} />
                  <Stat label="ΔΔG (proxy)" value={structure.ddg_kcal_mol} suffix=" kcal/mol" />
                  <Stat label="pLDDT mean" value={structure.af_mean_plddt} />
                  <Stat
                    label={`pLDDT @ ${ann?.aa_change?.position ?? "?"}`}
                    value={structure.variant_residue_plddt}
                    suffix={structure.variant_residue_plddt_band ? ` · ${structure.variant_residue_plddt_band}` : ""}
                  />
                </div>
                {structure.domain_at_position && (
                  <p className="mt-2 text-[13px] text-ink2 italic serif-italic">
                    falls inside <span className="text-oxblood">{structure.domain_at_position}</span>
                    {structure.in_active_site && " · within active site"}
                  </p>
                )}
              </EvidenceCard>
            )}

            {literature.length > 0 && (
              <EvidenceCard key="lit" eyebrow="literature · PubMed + Europe PMC · multilingual" title={`${literature.length} hits`} status={steps.literature.status} elapsedMs={steps.literature.elapsedMs} accent="leaf">
                <LiteratureList hits={literature} />
              </EvidenceCard>
            )}

            {liver && liver.in_panel && (
              <EvidenceCard key="lc" eyebrow="liver context · GTEx · HPA · Reactome" title="Tissue & pathway" status={steps.liver_context.status} elapsedMs={steps.liver_context.elapsedMs} accent="teal">
                <div className="grid grid-cols-2 gap-3 text-[13px]">
                  <Stat label="GTEx liver TPM" value={liver.gtex_liver_tpm} />
                  <Stat label="HPA liver" value={liver.hpa_liver_expression as any} />
                </div>
                {liver.reactome_pathways && liver.reactome_pathways.length > 0 && (
                  <div className="mt-3">
                    <p className="text-[10px] uppercase tracking-[0.2em] text-muted font-mono">Reactome</p>
                    <ul className="text-[12px] text-ink2 mt-1">
                      {liver.reactome_pathways.slice(0, 4).map((p) => <li key={p}>· {p}</li>)}
                    </ul>
                  </div>
                )}
              </EvidenceCard>
            )}

            {liver && liver.disease_spectrum && liver.disease_spectrum.length > 0 && (
              <EvidenceCard key="ds" eyebrow="disease spectrum · curated" title="Phenotypes caused by this gene" status="ok" accent="oxblood">
                <DiseaseSpectrumTable spectrum={liver.disease_spectrum} gene={ann?.gene_symbol} />
              </EvidenceCard>
            )}
          </AnimatePresence>
        </section>

        {/* Reasoning column */}
        <aside className="lg:col-span-5 space-y-4 lg:sticky lg:top-4 lg:self-start lg:max-h-[calc(100vh-2rem)] lg:overflow-y-auto pr-1">
          <h2 className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted mb-2">Synthesis</h2>
          <VerdictCard acmg={acmg ?? null} jobId={id} ready={!!report} />
          {acmg && (
            <div className="rounded-2xl bg-surface border hairline shadow-card p-5">
              <p className="text-[10px] uppercase tracking-[0.25em] text-muted font-mono mb-3">ACMG criteria applied</p>
              <AcmgChecklist criteria={acmg.criteria} />
            </div>
          )}
          <ReasoningPane markdown={reasoning} thinking={thinking} />
          <ChatComposer jobId={id} ready={!!report} />
        </aside>
      </div>
    </main>
  );
}

function KV({ k, v, mono = false }: { k: string; v: any; mono?: boolean }) {
  return (
    <div className="flex items-baseline gap-2 text-[13px] py-0.5">
      <span className="text-muted text-[11px] uppercase tracking-[0.18em] font-mono w-[72px] shrink-0">{k}</span>
      <span className={mono ? "font-mono text-ink" : "text-ink"}>{v ?? "—"}</span>
    </div>
  );
}

function Pred({ label, pred, score }: { label: string; pred: string | null | undefined; score: number | null | undefined }) {
  const tone = pred?.includes("damag") || pred?.includes("delet") ? "text-coral" : pred?.includes("benig") || pred?.includes("toler") ? "text-leaf" : "text-muted";
  return (
    <div className={"rounded-md bg-bg/40 px-2 py-1 " + tone}>
      <div className="text-[10px] uppercase tracking-[0.18em]">{label}</div>
      <div className="font-mono text-[12px]">{pred ?? "—"}{score !== null && score !== undefined ? ` ${typeof score === "number" ? score.toFixed(2) : score}` : ""}</div>
    </div>
  );
}

function PopBar({ label, af }: { label: string; af: number }) {
  const pct = Math.min(100, Math.max(0.5, af * 100 * 1000)); // visual scaling for rare AFs
  const tone = label.toLowerCase().includes("amr") || label.toLowerCase().includes("afr") ? "bg-amber" : "bg-oxblood/70";
  return (
    <div className="flex items-center gap-2 text-[11px] font-mono">
      <span className="w-[48px] text-muted">{label}</span>
      <div className="flex-1 h-1.5 bg-bg rounded-full overflow-hidden">
        <div className={"h-full " + tone} style={{ width: pct + "%" }} />
      </div>
      <span className="w-[80px] text-right text-ink2">{af.toExponential(1)}</span>
    </div>
  );
}

function Stat({ label, value, suffix = "" }: { label: string; value: number | null | undefined | string; suffix?: string }) {
  const display = value === null || value === undefined ? "—" :
    typeof value === "number" ? value.toFixed(2) : String(value);
  return (
    <div className="rounded-lg bg-bg/40 px-3 py-2">
      <div className="text-[10px] uppercase tracking-[0.18em] text-muted font-mono">{label}</div>
      <div className="font-display text-[18px] text-ink mt-0.5">{display}{suffix}</div>
    </div>
  );
}
