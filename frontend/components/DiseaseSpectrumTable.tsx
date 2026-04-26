"use client";
import type { DiseaseEntity } from "@/lib/types";

export function DiseaseSpectrumTable({ spectrum, gene }: { spectrum: DiseaseEntity[]; gene?: string | null }) {
  if (!spectrum || spectrum.length === 0) return null;
  return (
    <div className="-mx-1 overflow-x-auto">
      <p className="text-[12px] text-muted italic serif-italic mb-2">
        Clinical entities caused by variants in <span className="font-mono not-italic text-ink2">{gene}</span> — phenotype + inheritance + residual protein activity.
      </p>
      <table className="w-full text-[12px]">
        <thead>
          <tr className="text-muted text-[10px] uppercase tracking-[0.18em] border-b hairline font-mono">
            <th className="text-left py-2 pl-1">Condition</th>
            <th className="text-left py-2">Inheritance</th>
            <th className="text-left py-2">Residual</th>
            <th className="text-left py-2">Age onset</th>
            <th className="text-left py-2">GGT</th>
            <th className="text-left py-2 pr-1">Key features</th>
          </tr>
        </thead>
        <tbody>
          {spectrum.map((d, i) => (
            <tr key={i} className="border-b hairline/40 align-top">
              <td className="py-2 pl-1">
                <div className="font-display text-ink leading-tight">{d.abbrev}</div>
                <div className="text-[11px] text-muted italic serif-italic">{d.name}</div>
              </td>
              <td className="py-2 font-mono text-ink2">{d.inheritance ?? "—"}</td>
              <td className="py-2 font-mono text-ink2">{d.residual_activity ?? "—"}</td>
              <td className="py-2 font-mono text-ink2">{d.age_onset ?? "—"}</td>
              <td className="py-2 font-mono text-ink2">{d.ggt ?? "—"}</td>
              <td className="py-2 pr-1 text-ink2 leading-snug">
                {(d.features ?? []).map((f, j) => (
                  <span key={j} className="block before:content-['·_'] before:text-muted">
                    {f}
                  </span>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
