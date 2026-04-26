"use client";
import type { VEPAnnotation, VariantInput } from "@/lib/types";

export function StrandExplainer({ ann, variant }: { ann: VEPAnnotation; variant: VariantInput }) {
  if (ann.gene_strand !== -1) return null;
  const gRef = ann.genomic_ref ?? variant.ref;
  const gAlt = ann.genomic_alt ?? variant.alt;
  const cRef = ann.coding_ref;
  const cAlt = ann.coding_alt;

  return (
    <div className="rounded-2xl bg-amber/10 border border-amber/30 p-4 text-[13px] text-ink2">
      <div className="flex items-baseline justify-between mb-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-amber">strand mismatch warning</span>
        <span className="font-mono text-[10px] text-amber">{ann.gene_symbol} on minus (−) strand</span>
      </div>
      <p className="leading-relaxed mb-3">
        <strong>{ann.gene_symbol}</strong> is encoded on the <strong>antisense (minus) strand</strong> of chromosome{" "}
        {variant.chrom.replace("chr", "")}. The reference base reported in your VCF is on the forward (+) genomic strand,
        but every HGVS.c notation is on the transcript (−) strand. They are reverse complements of each other —
        any tool that mixes the two will appear inconsistent.
      </p>

      <div className="grid grid-cols-2 gap-3 font-mono">
        <div className="rounded-lg border hairline bg-surface px-3 py-2">
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted">+ strand (genomic)</div>
          <div className="text-[16px] text-ink mt-1">{gRef}<span className="text-muted px-1">→</span>{gAlt}</div>
          <div className="text-[10px] text-muted mt-1">what your VCF reports</div>
        </div>
        <div className="rounded-lg border hairline bg-surface px-3 py-2">
          <div className="text-[10px] uppercase tracking-[0.18em] text-oxblood">− strand (HGVS.c)</div>
          <div className="text-[16px] text-oxblood mt-1">{cRef ?? "?"}<span className="text-muted px-1">→</span>{cAlt ?? "?"}</div>
          <div className="text-[10px] text-muted mt-1">what literature, ClinVar use</div>
        </div>
      </div>
    </div>
  );
}
