"use client";
import clsx from "clsx";
import type { AASubstitution } from "@/lib/types";

export function AASubstitutionCard({ sub }: { sub: AASubstitution }) {
  const a = sub.wild_type;
  const b = sub.variant;
  const cls = "py-1.5 text-[12px]";
  const hi = (delta: number | null | undefined) =>
    delta == null ? "" : Math.abs(delta) > 60 ? "text-coral" : Math.abs(delta) > 20 ? "text-amber" : "text-ink2";

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-center gap-3 py-2">
        <AAGlyph aa={a} role="wild-type" />
        <span className="font-display text-[28px] text-muted">→</span>
        <AAGlyph aa={b} role="variant" />
      </div>

      <table className="w-full text-[12px]">
        <thead>
          <tr className="text-muted border-b hairline font-mono uppercase tracking-[0.18em] text-[10px]">
            <th className="text-left py-1.5"></th>
            <th className="text-right py-1.5">{a.three}</th>
            <th className="text-right py-1.5">{b.three}</th>
            <th className="text-right py-1.5">Δ</th>
          </tr>
        </thead>
        <tbody className="font-mono">
          <Row label="MW (Da)"          a={a.mw}              b={b.mw} />
          <Row label="Volume (Å³)"      a={a.volume}          b={b.volume}          delta={sub.delta_volume}          hi={hi(sub.delta_volume)} />
          <Row label="Hydrophobicity"   a={a.hydrophobicity}  b={b.hydrophobicity}  delta={sub.delta_hydrophobicity} />
          <Row label="Charge"           a={a.charge}          b={b.charge}          delta={sub.delta_charge} />
        </tbody>
      </table>

      <dl className="text-[12px] space-y-1">
        <Row2 label="Side chain"   wt={a.side_chain}   mut={b.side_chain} />
        <Row2 label="H-bonding"    wt={a.h_bond}       mut={b.h_bond} />
        <Row2 label="Aromatic"     wt={a.aromatic ? "yes" : "no"} mut={b.aromatic ? "yes" : "no"} />
      </dl>

      {sub.summary_flags && sub.summary_flags.length > 0 && (
        <div className="pt-2 border-t hairline">
          <p className="text-[10px] uppercase tracking-[0.2em] text-muted font-mono mb-1">Predicted impact</p>
          <ul className="text-[12px] text-ink2 space-y-1">
            {sub.summary_flags.map((f, i) => (
              <li key={i} className="flex gap-1.5"><span className="text-oxblood">·</span> {f}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function AAGlyph({ aa, role }: { aa: any; role: "wild-type" | "variant" }) {
  const tone = role === "wild-type"
    ? "border-teal/40 bg-teal/5 text-teal"
    : "border-oxblood/40 bg-oxblood/5 text-oxblood";
  return (
    <div className={clsx("flex flex-col items-center justify-center w-[110px] h-[110px] rounded-2xl border-2", tone)}>
      <span className="font-display text-[44px] leading-none">{aa.code}</span>
      <span className="font-mono text-[10px] mt-1 uppercase tracking-[0.18em]">{aa.three}</span>
      <span className="text-[10px] mt-0.5 italic serif-italic">{aa.name}</span>
    </div>
  );
}

function Row({ label, a, b, delta, hi }: { label: string; a: any; b: any; delta?: number | null; hi?: string }) {
  return (
    <tr className="border-b hairline/40">
      <td className="py-1 text-muted text-[11px] uppercase tracking-[0.15em]">{label}</td>
      <td className="py-1 text-right text-ink">{fmt(a)}</td>
      <td className="py-1 text-right text-ink">{fmt(b)}</td>
      <td className={clsx("py-1 text-right", hi)}>{delta == null ? "—" : (delta > 0 ? "+" : "") + (typeof delta === "number" ? delta.toFixed(1) : "")}</td>
    </tr>
  );
}

function Row2({ label, wt, mut }: { label: string; wt: any; mut: any }) {
  return (
    <div className="grid grid-cols-[110px_1fr] gap-2 py-0.5">
      <dt className="text-[10px] uppercase tracking-[0.18em] text-muted font-mono">{label}</dt>
      <dd className="text-ink2">
        <span className="text-teal">{wt ?? "—"}</span> → <span className="text-oxblood">{mut ?? "—"}</span>
      </dd>
    </div>
  );
}

function fmt(v: any): string {
  if (v == null) return "—";
  if (typeof v === "number") return v.toFixed(2).replace(/\.00$/, "");
  return String(v);
}
