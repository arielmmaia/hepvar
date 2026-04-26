"use client";
import clsx from "clsx";
import type { GnomadFreq } from "@/lib/types";

// gnomAD v4 ancestry-group ordering. Lower-ancestry-coverage cohorts (amr, afr) are
// highlighted because the equity premise — non-European patients are under-represented
// in variant databases — is the central methodological claim of HepVar.
const POPS: { key: string; label: string; ancestry: string; highlight?: boolean }[] = [
  { key: "nfe", label: "NFE",  ancestry: "Non-Finnish European" },
  { key: "fin", label: "FIN",  ancestry: "Finnish" },
  { key: "amr", label: "AMR",  ancestry: "Latin / Admixed American", highlight: true },
  { key: "afr", label: "AFR",  ancestry: "African / African-American", highlight: true },
  { key: "eas", label: "EAS",  ancestry: "East Asian" },
  { key: "sas", label: "SAS",  ancestry: "South Asian" },
  { key: "mid", label: "MID",  ancestry: "Middle Eastern" },
  { key: "asj", label: "ASJ",  ancestry: "Ashkenazi Jewish" },
  { key: "remaining", label: "REM", ancestry: "Remaining" },
];

export function PopulationBarChart({ gnomad }: { gnomad: GnomadFreq }) {
  const pops = gnomad.af_populations ?? {};
  // Compute scaling: log-scale bars because rare-variant frequencies span many orders
  // of magnitude. Bar = log10(af) mapped to [0, 100%]; absent (af=0 or null) → 0%.
  const values = POPS.map((p) => ({ ...p, af: pops[p.key] ?? 0 }));
  const presentVals = values.filter((v) => v.af > 0).map((v) => v.af);
  const maxLog = presentVals.length ? Math.log10(Math.max(...presentVals)) : 0;
  const minLog = -7; // gnomAD floor — singletons in 1.4M alleles ≈ 7 × 10⁻⁷

  return (
    <div className="space-y-2.5">
      <div className="flex items-baseline justify-between mb-1">
        <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted">
          per-ancestry allele frequency · gnomAD v4
        </span>
        <span className="font-mono text-[10px] text-amber italic serif-italic">
          highlighted: under-represented in curated variant DBs
        </span>
      </div>
      {values.map((v) => {
        const present = v.af > 0;
        const widthPct = present
          ? Math.max(2, ((Math.log10(v.af) - minLog) / Math.max(0.001, maxLog - minLog)) * 100)
          : 0;
        return (
          <div key={v.key} className="grid grid-cols-[80px_1fr_120px] gap-2 items-center text-[12px]">
            <div className="font-mono">
              <span className={clsx(v.highlight ? "text-oxblood" : "text-ink2")}>{v.label}</span>
              <span className="text-muted text-[10px] ml-1.5">{v.ancestry}</span>
            </div>
            <div className="h-3 bg-bg/40 rounded-sm overflow-hidden relative">
              <div
                className={clsx(
                  "h-full transition-all duration-500",
                  present ? (v.highlight ? "bg-oxblood/80" : "bg-teal/70") : "bg-transparent"
                )}
                style={{ width: widthPct + "%" }}
              />
              {!present && (
                <span className="absolute inset-0 flex items-center pl-2 text-[10px] font-mono text-muted/70 italic">absent</span>
              )}
            </div>
            <div className="font-mono text-right text-ink2">
              {present ? v.af.toExponential(2) : "—"}
            </div>
          </div>
        );
      })}
      {gnomad.notes && (
        <p className="mt-3 text-[12px] text-oxblood italic serif-italic border-l-2 border-oxblood pl-2">
          {gnomad.notes}
        </p>
      )}
    </div>
  );
}
