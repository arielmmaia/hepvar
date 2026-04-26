"use client";
import clsx from "clsx";
import type { AlphaGenomeModality, AlphaGenomePrediction } from "@/lib/types";

const MODALITY_LABEL: Record<string, { name: string; assay: string; tone: string }> = {
  rna_seq:            { name: "RNA-seq",          assay: "expression",          tone: "text-oxblood bg-oxblood/10" },
  splice_sites:       { name: "Splice sites",     assay: "ΔPSI",                tone: "text-amber bg-amber/10" },
  splice_site_usage:  { name: "Splice usage",     assay: "ΔSSU",                tone: "text-amber bg-amber/15" },
  atac:               { name: "ATAC-seq",         assay: "chromatin",           tone: "text-teal bg-teal/10" },
  cage:               { name: "CAGE",             assay: "transcription start", tone: "text-leaf bg-leaf/10" },
  chip_tf:            { name: "ChIP-TF",          assay: "TF binding",          tone: "text-coral bg-coral/10" },
  chip_histone:       { name: "ChIP-histone",     assay: "histone marks",       tone: "text-muted bg-muted/10" },
};

export function AlphaGenomePanel({ pred }: { pred: AlphaGenomePrediction }) {
  if (!pred.modalities || pred.modalities.length === 0) {
    return (
      <div>
        <div className="grid grid-cols-3 gap-3 text-[13px]">
          <Stat label="splice Δ" value={pred.splice_delta} />
          <Stat label="expr log2FC" value={pred.expression_log2fc} />
          <Stat label="ATAC Δ" value={pred.chromatin_accessibility_delta} />
        </div>
        {pred.flags && pred.flags.length > 0 && (
          <ul className="mt-3 text-[12px] text-amber space-y-1">
            {pred.flags.map((f, i) => <li key={i}>· {f}</li>)}
          </ul>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {pred.modalities.map((m) => (
        <ModalityRow key={m.output_type} m={m} />
      ))}
      {pred.flags && pred.flags.length > 0 && (
        <ul className="pt-2 border-t hairline text-[12px] text-amber space-y-1">
          {pred.flags.map((f, i) => <li key={i}>· {f}</li>)}
        </ul>
      )}
    </div>
  );
}

function ModalityRow({ m }: { m: AlphaGenomeModality }) {
  const meta = MODALITY_LABEL[m.output_type] ?? { name: m.output_type, assay: "—", tone: "text-ink2 bg-bg/40" };
  const max = m.max_abs_delta ?? 0;
  const flagged = max >= 0.2;
  return (
    <div className="rounded-xl border hairline px-3 py-2.5 bg-surface">
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-baseline gap-2">
          <span className={clsx("rounded-md px-1.5 py-[1px] text-[10px] font-mono uppercase tracking-[0.15em]", meta.tone)}>
            {meta.name}
          </span>
          <span className="text-[11px] italic serif-italic text-muted">{meta.assay}</span>
          <span className="text-[10px] font-mono text-muted">{m.n_tracks ?? 0} tracks</span>
        </div>
        <div className="font-mono text-[12px] text-ink">
          max |Δ| <strong className={flagged ? "text-coral" : "text-ink"}>{max.toFixed(3)}</strong>
        </div>
      </div>
      {m.sparkline && m.sparkline.length > 0 && (
        <Sparkline data={m.sparkline} window={m.sparkline_window ?? 0} />
      )}
    </div>
  );
}

function Sparkline({ data, window }: { data: number[]; window: number }) {
  // Render as inline SVG, signed (positive = above midline = oxblood, negative = teal)
  const w = 280, h = 32;
  const max = Math.max(0.001, ...data.map((v) => Math.abs(v)));
  const mid = h / 2;
  const xStep = w / (data.length - 1);
  const points = data.map((v, i) => {
    const y = mid - (v / max) * (mid - 2);
    return `${i * xStep},${y}`;
  }).join(" ");
  // Highlight middle (variant position)
  const variantX = w / 2;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-8" preserveAspectRatio="none">
      {/* Centre line */}
      <line x1={0} y1={mid} x2={w} y2={mid} stroke="currentColor" strokeWidth={0.4} className="text-muted/40" />
      {/* Variant marker */}
      <line x1={variantX} y1={0} x2={variantX} y2={h} stroke="currentColor" strokeWidth={0.6} strokeDasharray="2 2" className="text-oxblood/50" />
      {/* Series */}
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth={1.2} className="text-oxblood" />
      {/* Window label */}
      <text x={w - 2} y={h - 1} textAnchor="end" fontSize="7" fill="currentColor" className="text-muted font-mono">
        ±{window} bp
      </text>
    </svg>
  );
}

function Stat({ label, value }: { label: string; value?: number | null }) {
  return (
    <div className="rounded-md bg-bg/40 px-2.5 py-1.5">
      <div className="text-[10px] uppercase tracking-[0.18em] text-muted font-mono">{label}</div>
      <div className="font-display text-[16px] text-ink">{value == null ? "—" : value.toFixed(3)}</div>
    </div>
  );
}
