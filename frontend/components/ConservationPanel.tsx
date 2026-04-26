"use client";
import clsx from "clsx";
import type { ConservationPanel as ConservationPanelType } from "@/lib/types";

export function ConservationPanel({ panel }: { panel: ConservationPanelType }) {
  if (!panel.species || panel.species.length === 0) return null;
  const pct = panel.pct_conserved_at_position ?? 0;
  return (
    <div>
      <div className="flex items-baseline justify-between mb-3">
        <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted">
          conservation @ residue {panel.variant_position}
        </span>
        <span className="font-mono text-[12px]">
          <strong className={pct >= 90 ? "text-coral" : pct >= 60 ? "text-amber" : "text-teal"}>
            {pct.toFixed(1)}%
          </strong>{" "}
          <span className="text-muted">conserved across {panel.n_orthologs} species</span>
        </span>
      </div>

      <div className="space-y-1">
        {panel.species.map((s) => {
          const tone = s.is_gap
            ? "bg-bg/40 text-muted"
            : s.matches_human
              ? "bg-coral/10 text-coral border border-coral/30"
              : "bg-amber/10 text-amber border border-amber/30";
          const label = s.common_name ?? s.species.replace(/_/g, " ");
          return (
            <div key={s.species} className="grid grid-cols-[28px_1fr_56px] gap-2 items-center text-[12px]">
              <div className={clsx("h-7 w-7 rounded-md flex items-center justify-center font-mono font-semibold", tone)}>
                {s.is_gap ? "–" : s.residue ?? "?"}
              </div>
              <div className="truncate">
                <span className="text-ink2">{label}</span>
                <span className="text-muted text-[10px] ml-1.5 italic serif-italic">{s.species.replace(/_/g, " ")}</span>
              </div>
              <div className="text-right font-mono text-[10px] text-muted">
                {s.perc_id != null ? `${s.perc_id.toFixed(0)}%` : "—"}
              </div>
            </div>
          );
        })}
      </div>

      <p className="mt-3 text-[11px] text-muted italic serif-italic">
        Coral = identical to human <strong className="not-italic font-mono text-coral">{panel.human_residue}</strong> at this
        position. Amber = different residue. Bar at right = overall ortholog protein identity vs human.
      </p>
    </div>
  );
}
