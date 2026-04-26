"use client";
import clsx from "clsx";
import type { AudienceMode } from "@/lib/audience";

const OPTIONS: { value: AudienceMode; label: string; sub: string }[] = [
  { value: "technical", label: "Technical",  sub: "audit · raw values" },
  { value: "clinician", label: "Clinician",  sub: "hepatology consult" },
  { value: "patient",   label: "Patient",    sub: "plain language" },
];

export function AudienceToggle({
  mode,
  onChange,
}: {
  mode: AudienceMode;
  onChange: (mode: AudienceMode) => void;
}) {
  return (
    <div className="rounded-2xl bg-surface border hairline p-1.5 grid grid-cols-3 gap-1">
      {OPTIONS.map((o) => {
        const active = o.value === mode;
        return (
          <button
            key={o.value}
            onClick={() => onChange(o.value)}
            className={clsx(
              "rounded-xl px-3 py-2 text-left transition focus:outline-none",
              active
                ? "bg-oxblood text-surface shadow-card"
                : "bg-transparent text-ink2 hover:bg-bg/40",
            )}
          >
            <div className="font-display text-[14px] leading-tight">{o.label}</div>
            <div className={clsx("text-[10px] mt-0.5 font-mono uppercase tracking-[0.15em]", active ? "text-surface/70" : "text-muted")}>
              {o.sub}
            </div>
          </button>
        );
      })}
    </div>
  );
}
