"use client";
import clsx from "clsx";
import type { SequenceContext, SequenceAnnotation } from "@/lib/types";

const KIND_TONE: Record<string, { dot: string; text: string; label: string }> = {
  variant:       { dot: "bg-oxblood",  text: "text-oxblood",  label: "variant" },
  active_site:   { dot: "bg-coral",    text: "text-coral",    label: "active site" },
  binding_site:  { dot: "bg-amber",    text: "text-amber",    label: "binding site" },
  domain_start:  { dot: "bg-teal",     text: "text-teal",     label: "domain start" },
  domain_end:    { dot: "bg-teal/70",  text: "text-teal",     label: "domain end" },
  motif:         { dot: "bg-leaf",     text: "text-leaf",     label: "motif" },
  modified:      { dot: "bg-muted",    text: "text-muted",    label: "PTM site" },
};

export function SequenceContextStrip({ ctx }: { ctx: SequenceContext }) {
  if (!ctx.sequence || ctx.variant_offset == null) return null;
  const seq = ctx.sequence;
  const annsByPos = new Map<number, SequenceAnnotation[]>();
  for (const a of ctx.annotations ?? []) {
    if (!annsByPos.has(a.position)) annsByPos.set(a.position, []);
    annsByPos.get(a.position)!.push(a);
  }

  // Annotation kinds present (for the legend)
  const presentKinds = Array.from(new Set((ctx.annotations ?? []).map((a) => a.kind))).filter(
    (k) => KIND_TONE[k]
  );

  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted">
          local context · ±{Math.floor((seq.length - 1) / 2)} aa around residue {ctx.variant_position}
        </span>
        <span className="font-mono text-[10px] text-muted">
          {ctx.start}–{ctx.end} on {ctx.accession}
        </span>
      </div>

      {/* Sequence row: each residue as a tile. */}
      <div className="overflow-x-auto -mx-1 pb-1">
        <div className="inline-flex font-mono text-[14px]">
          {seq.split("").map((aa, i) => {
            const absPos = (ctx.start ?? 1) + i;
            const isVariant = i === ctx.variant_offset;
            const anns = annsByPos.get(absPos) ?? [];
            const tone =
              isVariant ? "bg-oxblood text-surface ring-2 ring-oxblood/60" :
              anns.find((a) => a.kind === "active_site") ? "bg-coral/15 text-coral ring-1 ring-coral/40" :
              anns.find((a) => a.kind === "binding_site") ? "bg-amber/15 text-amber ring-1 ring-amber/40" :
              anns.find((a) => a.kind === "motif") ? "bg-leaf/15 text-leaf" :
              anns.find((a) => a.kind?.startsWith("domain")) ? "bg-teal/15 text-teal" :
              "bg-bg/40 text-ink2";
            return (
              <div
                key={i}
                title={anns.length > 0 ? anns.map((a) => `@${a.position}: ${a.label ?? a.kind}`).join("\n") : `${aa} @ ${absPos}`}
                className={clsx(
                  "flex flex-col items-center justify-center w-7 h-9 mx-[1px] rounded-md transition-colors cursor-default",
                  tone,
                  isVariant && "scale-110"
                )}
              >
                <span className="leading-none font-semibold">{aa}</span>
                <span className="text-[8px] mt-0.5 leading-none opacity-70">
                  {absPos % 5 === 0 || isVariant ? absPos : ""}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Annotations list */}
      {(ctx.annotations?.length ?? 0) > 1 && (
        <div className="mt-3 pt-2 border-t hairline space-y-1">
          {(ctx.annotations ?? [])
            .filter((a) => a.kind !== "variant")
            .map((a, i) => {
              const tone = KIND_TONE[a.kind] ?? KIND_TONE.modified;
              const sign = a.relative > 0 ? "+" : "";
              return (
                <div key={i} className="flex items-baseline gap-2 text-[11px]">
                  <span className={clsx("inline-block w-1.5 h-1.5 rounded-full", tone.dot)} />
                  <span className="font-mono text-muted w-[60px]">{a.position} ({sign}{a.relative})</span>
                  <span className={clsx("italic serif-italic", tone.text)}>{a.label ?? tone.label}</span>
                </div>
              );
            })}
        </div>
      )}

      {/* Legend */}
      {presentKinds.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-3 text-[10px] font-mono uppercase tracking-[0.18em] text-muted">
          {presentKinds.map((k) => (
            <span key={k} className="flex items-center gap-1">
              <span className={clsx("inline-block w-2 h-2 rounded-full", KIND_TONE[k]?.dot)} />
              {KIND_TONE[k]?.label ?? k}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
