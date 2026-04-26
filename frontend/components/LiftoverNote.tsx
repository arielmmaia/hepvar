"use client";
import type { LiftoverInfo } from "@/lib/types";

export function LiftoverNote({ info, geneSymbol }: { info: LiftoverInfo; geneSymbol?: string | null }) {
  if (!info || !info.target_pos) return null;
  const warn = !!info.ambiguity_warning && info.wrong_assembly_gene;
  return (
    <div className={"rounded-2xl border px-4 py-3 text-[13px] " + (warn ? "border-coral/40 bg-coral/5" : "border-hairline bg-bg/40")}>
      <div className="flex items-center justify-between mb-1">
        <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted">assembly · liftover</span>
        {warn && <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-coral">⚠ build mismatch trap</span>}
      </div>
      <div className="grid sm:grid-cols-2 gap-3 font-mono">
        <div className="rounded-md bg-surface px-3 py-1.5">
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted">{info.source_assembly} (input)</div>
          <div className="text-ink">chr{info.source_pos != null ? info.target_chrom != null ? "…" : "" : ""}{info.target_chrom ?? ""}:{info.source_pos}</div>
        </div>
        <div className="rounded-md bg-surface px-3 py-1.5">
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted">{info.target_assembly} (lifted)</div>
          <div className="text-ink">chr{info.target_chrom}:{info.target_pos}</div>
        </div>
      </div>
      {warn && (
        <p className="mt-3 text-[12px] text-coral leading-relaxed">
          If this position number is mis-interpreted as <strong>{info.target_assembly}</strong>, it overlaps{" "}
          <strong className="font-mono">{info.wrong_assembly_gene}</strong>, not <strong className="font-mono">{geneSymbol}</strong>.
          Confirm the assembly on the source report — same number, different gene.
        </p>
      )}
    </div>
  );
}
