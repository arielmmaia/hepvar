"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { startAnalysis } from "@/lib/api";

type Example = { label: string; gene: string; ann: string; chrom: string; pos: number; ref: string; alt: string; flag: string };

const EXAMPLES: Example[] = [
  { label: "ABCB4 — LPAC / PFIC3", gene: "ABCB4", ann: "Brazilian patient w/ chronic cholestasis", chrom: "chr7", pos: 87408188, ref: "T", alt: "C", flag: "🇧🇷" },
  { label: "ATP7B — Wilson disease", gene: "ATP7B", ann: "p.His1069Gln (rs76151636)", chrom: "chr13", pos: 51932119, ref: "C", alt: "T", flag: "🩺" },
  { label: "SERPINA1 — α1-AT (Z allele)", gene: "SERPINA1", ann: "p.Glu342Lys (rs28929474)", chrom: "chr14", pos: 94378610, ref: "C", alt: "T", flag: "🫁" },
];

export function VariantInput() {
  const router = useRouter();
  const [chrom, setChrom] = useState("chr7");
  const [pos, setPos] = useState("87408188");
  const [ref, setRef] = useState("T");
  const [alt, setAlt] = useState("C");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e?: React.FormEvent) {
    e?.preventDefault();
    setBusy(true); setErr(null);
    try {
      const v = { chrom, pos: parseInt(pos, 10), ref: ref.toUpperCase(), alt: alt.toUpperCase(), assembly: "GRCh38" as const };
      const { jobId } = await startAnalysis(v);
      router.push(`/analyze/${jobId}`);
    } catch (e: any) {
      setErr(e?.message ?? "failed");
      setBusy(false);
    }
  }

  function loadExample(ex: Example) {
    setChrom(ex.chrom); setPos(String(ex.pos)); setRef(ex.ref); setAlt(ex.alt);
  }

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
      className="rounded-3xl bg-surface border hairline border shadow-card p-8 md:p-10"
    >
      <form onSubmit={submit} className="grid grid-cols-12 gap-3 items-end">
        <Field label="Chromosome" className="col-span-3">
          <input value={chrom} onChange={e => setChrom(e.target.value)} className={inputCls} placeholder="chr7" />
        </Field>
        <Field label="Position (GRCh38)" className="col-span-4">
          <input value={pos} onChange={e => setPos(e.target.value)} className={inputCls} placeholder="87408188" />
        </Field>
        <Field label="Ref" className="col-span-2">
          <input value={ref} onChange={e => setRef(e.target.value)} className={inputCls} maxLength={4} />
        </Field>
        <Field label="Alt" className="col-span-2">
          <input value={alt} onChange={e => setAlt(e.target.value)} className={inputCls} maxLength={4} />
        </Field>
        <button
          type="submit" disabled={busy}
          className="col-span-1 h-[58px] rounded-2xl bg-oxblood text-surface font-display font-medium text-lg tracking-tight hover:opacity-95 disabled:opacity-50 transition"
        >
          {busy ? "…" : "→"}
        </button>
      </form>
      {err && <p className="mt-3 text-sm text-coral">{err}</p>}

      <div className="mt-7 pt-6 border-t hairline">
        <p className="text-[11px] uppercase tracking-[0.2em] text-muted mb-3">Demo variants</p>
        <div className="grid md:grid-cols-3 gap-3">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.label} type="button" onClick={() => loadExample(ex)}
              className="text-left rounded-2xl border hairline px-4 py-3 hover:border-oxblood hover:bg-bg/50 transition group"
            >
              <div className="flex items-baseline justify-between">
                <span className="font-display font-semibold text-ink">{ex.gene}</span>
                <span className="text-xs text-muted">{ex.flag}</span>
              </div>
              <div className="text-[13px] text-ink2 mt-0.5">{ex.label.split("—")[1]?.trim()}</div>
              <div className="text-[11px] text-muted mt-1 font-mono">{ex.chrom}:{ex.pos} {ex.ref}{">"}{ex.alt}</div>
              <div className="text-[11px] italic text-muted mt-1 serif-italic">{ex.ann}</div>
            </button>
          ))}
        </div>
      </div>
    </motion.section>
  );
}

function Field({ label, children, className = "" }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <label className={"flex flex-col gap-1 " + className}>
      <span className="text-[11px] uppercase tracking-[0.2em] text-muted">{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  "w-full h-[58px] rounded-2xl border hairline bg-bg/40 px-4 font-mono text-base text-ink placeholder:text-muted/60 focus:border-oxblood focus:outline-none focus:ring-0 transition";
