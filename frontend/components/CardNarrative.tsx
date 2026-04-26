"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useTranslated, type AudienceMode } from "@/lib/audience";

/**
 * Small narrative paragraph rendered above an evidence card's data when the
 * audience mode is non-technical. The data tables/charts inside the card stay
 * unchanged — this is just a "what does this mean" summary.
 */
export function CardNarrative({
  jobId,
  card,
  mode,
  ready = true,
}: {
  jobId: string;
  card: string;
  mode: AudienceMode;
  ready?: boolean;
}) {
  const { text, loading } = useTranslated(jobId, "card", mode, card, ready && mode !== "technical");

  if (mode === "technical") return null;
  if (!text && !loading) return null;

  return (
    <div className="mb-3 px-3 py-2 rounded-lg bg-bg/60 border-l-2 border-oxblood/40 text-[12.5px] leading-relaxed text-ink2 prose-clinical">
      {loading && !text ? (
        <span className="text-muted italic serif-italic">Re-framing for {mode}…</span>
      ) : (
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
      )}
    </div>
  );
}
