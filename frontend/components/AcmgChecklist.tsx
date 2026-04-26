"use client";
import clsx from "clsx";
import type { ACMGCriterion } from "@/lib/types";

export function AcmgChecklist({ criteria }: { criteria: ACMGCriterion[] }) {
  if (!criteria || criteria.length === 0) {
    return <div className="text-muted text-sm">No criteria yet.</div>;
  }
  return (
    <ul className="grid sm:grid-cols-2 gap-2">
      {criteria.map((c) => (
        <li
          key={c.code}
          className={clsx(
            "rounded-xl border hairline px-3 py-2 group",
            c.weight > 0 ? "bg-oxblood/[0.04]" : "bg-teal/[0.05]",
          )}
          title={c.rationale ?? ""}
        >
          <div className="flex items-baseline justify-between">
            <span className="font-mono font-semibold text-ink">{c.code}</span>
            <span className={clsx("font-mono text-xs", c.weight > 0 ? "text-oxblood" : "text-teal")}>
              {c.weight > 0 ? "+" : ""}{c.weight}
            </span>
          </div>
          <p className="text-[12px] text-ink2 mt-1 leading-snug">{c.rationale}</p>
        </li>
      ))}
    </ul>
  );
}
