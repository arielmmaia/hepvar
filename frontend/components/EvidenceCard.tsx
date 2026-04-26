"use client";
import { motion } from "framer-motion";
import { StatusDot } from "./StatusDot";
import type { EvidenceStatus } from "@/lib/types";

export function EvidenceCard({
  title, eyebrow, status, elapsedMs, children, accent,
}: {
  title: string;
  eyebrow: string;
  status: EvidenceStatus;
  elapsedMs?: number;
  children?: React.ReactNode;
  accent?: "oxblood" | "teal" | "amber" | "leaf";
}) {
  const accentClass = {
    oxblood: "before:bg-oxblood",
    teal: "before:bg-teal",
    amber: "before:bg-amber",
    leaf: "before:bg-leaf",
  }[accent ?? "oxblood"];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}
      className={
        "relative rounded-2xl bg-surface border hairline shadow-card p-5 overflow-hidden " +
        "before:absolute before:left-0 before:top-0 before:bottom-0 before:w-[3px] " + accentClass
      }
    >
      <div className="flex items-baseline justify-between mb-3">
        <div className="flex items-center gap-2">
          <StatusDot status={status} />
          <span className="text-[11px] uppercase tracking-[0.2em] text-muted font-mono">{eyebrow}</span>
        </div>
        {elapsedMs !== undefined && (
          <span className="text-[10px] text-muted font-mono">{elapsedMs}ms</span>
        )}
      </div>
      <h3 className="font-display text-[19px] text-ink leading-snug mb-2">{title}</h3>
      <div className="text-[14px] text-ink2 leading-relaxed">{children}</div>
    </motion.div>
  );
}
