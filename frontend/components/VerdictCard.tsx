"use client";
import { motion } from "framer-motion";
import clsx from "clsx";
import type { ACMGResult } from "@/lib/types";

const LABEL_COLOR: Record<string, string> = {
  Pathogenic: "bg-coral text-surface",
  "Likely Pathogenic": "bg-oxblood text-surface",
  VUS: "bg-amber text-surface",
  "Likely Benign": "bg-leaf/80 text-surface",
  Benign: "bg-teal text-surface",
};

export function VerdictCard({ acmg, jobId, ready }: { acmg: ACMGResult | null | undefined; jobId?: string; ready?: boolean }) {
  if (!acmg) {
    return (
      <div className="rounded-3xl border-2 border-dashed hairline p-8 text-center text-muted">
        <span className="font-display italic">Awaiting ACMG synthesis…</span>
      </div>
    );
  }
  const cls = LABEL_COLOR[acmg.label] ?? "bg-ink text-surface";
  const post = acmg.posterior !== null && acmg.posterior !== undefined ? acmg.posterior : null;
  return (
    <motion.section
      initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-3xl bg-surface border hairline shadow-verdict overflow-hidden"
    >
      <div className={clsx("px-7 py-6 flex items-center justify-between", cls)}>
        <div>
          <p className="text-[11px] uppercase tracking-[0.25em] opacity-80 font-mono">ACMG / AMP classification</p>
          <h2 className="font-display text-[34px] leading-none mt-1 tracking-tightest">{acmg.label}</h2>
        </div>
        <div className="text-right font-mono">
          <p className="text-[11px] uppercase tracking-[0.2em] opacity-80">Posterior</p>
          <p className="text-3xl font-semibold">{post !== null ? (post * 100).toFixed(1) + "%" : "—"}</p>
        </div>
      </div>
      <div className="px-7 py-4 flex justify-between text-[13px] text-ink2 font-mono">
        <span>score <span className="text-ink font-semibold">{acmg.score >= 0 ? "+" : ""}{acmg.score}</span></span>
        <span>confidence <span className="text-ink font-semibold">{acmg.confidence}</span></span>
        <span>{acmg.criteria.filter(c => c.applied).length} criteria applied</span>
      </div>
      {jobId && ready && (
        <div className="px-7 pb-4">
          <PdfButton jobId={jobId} />
        </div>
      )}
    </motion.section>
  );
}

function PdfButton({ jobId }: { jobId: string }) {
  const apiBase =
    (typeof window !== "undefined" && (window as any).__HEPVAR_API__) ||
    process.env.NEXT_PUBLIC_API_BASE ||
    "http://localhost:8000";
  return (
    <a
      href={`${apiBase}/api/jobs/${jobId}/pdf`}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-2 rounded-full border hairline bg-surface px-4 py-1.5 text-[12px] font-mono text-ink2 hover:border-oxblood hover:text-oxblood transition"
    >
      ↓ download manuscript-style PDF report
    </a>
  );
}
