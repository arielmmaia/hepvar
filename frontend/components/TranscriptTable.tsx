"use client";
import clsx from "clsx";
import type { TranscriptConsequence } from "@/lib/types";

export function TranscriptTable({ transcripts }: { transcripts: TranscriptConsequence[] }) {
  if (!transcripts || transcripts.length === 0) return null;
  return (
    <div className="-mx-1 overflow-x-auto">
      <table className="w-full text-[12px] font-mono">
        <thead>
          <tr className="text-muted text-[10px] uppercase tracking-[0.18em] border-b hairline">
            <th className="text-left py-2 pl-1">Transcript</th>
            <th className="text-left py-2">HGVS.c</th>
            <th className="text-left py-2">HGVS.p</th>
            <th className="text-left py-2">Consequence</th>
            <th className="text-right py-2 pr-1">AA pos</th>
          </tr>
        </thead>
        <tbody>
          {transcripts.map((t, i) => (
            <tr key={i} className="border-b hairline/40 hover:bg-bg/40 transition">
              <td className="py-2 pl-1 align-top">
                <div className="flex items-center gap-1.5">
                  <span className={clsx("text-[11px]", t.canonical ? "text-oxblood font-semibold" : "text-ink2")}>
                    {t.transcript_id}
                  </span>
                  {t.canonical && <Pill tone="oxblood">canonical</Pill>}
                  {t.mane_select && <Pill tone="teal">MANE</Pill>}
                </div>
                {t.refseq_match && <div className="text-[10px] text-muted mt-0.5">{t.refseq_match}</div>}
                {t.transcript_biotype && t.transcript_biotype !== "protein_coding" && (
                  <div className="text-[10px] text-muted italic serif-italic mt-0.5">{t.transcript_biotype.replace(/_/g, " ")}</div>
                )}
              </td>
              <td className="py-2 align-top text-ink2">{t.hgvs_c?.split(":").pop() || "—"}</td>
              <td className="py-2 align-top text-ink2">{t.hgvs_p?.split(":").pop() || "—"}</td>
              <td className="py-2 align-top text-ink2 text-[11px] uppercase tracking-[0.1em]">{t.consequence?.replace(/_/g, " ") || "—"}</td>
              <td className="py-2 pr-1 align-top text-right">
                {t.aa_position ? (
                  <span className="text-ink">
                    {t.aa_ref}<strong>{t.aa_position}</strong>{t.aa_alt}
                  </span>
                ) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Pill({ children, tone }: { children: React.ReactNode; tone: "oxblood" | "teal" }) {
  const cls = tone === "oxblood" ? "bg-oxblood/10 text-oxblood" : "bg-teal/10 text-teal";
  return <span className={clsx("rounded-full px-1.5 py-[1px] text-[9px] font-mono uppercase tracking-[0.15em]", cls)}>{children}</span>;
}
