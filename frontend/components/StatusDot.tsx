import clsx from "clsx";
import type { EvidenceStatus } from "@/lib/types";

const COLOR: Record<EvidenceStatus, string> = {
  pending: "bg-hairline",
  running: "bg-amber dot-pulse",
  ok: "bg-leaf",
  partial: "bg-amber",
  missing: "bg-hairline",
  error: "bg-coral",
};

export function StatusDot({ status }: { status: EvidenceStatus }) {
  return <span className={clsx("inline-block h-2 w-2 rounded-full", COLOR[status])} />;
}
