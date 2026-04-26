"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function ReasoningPane({ markdown, thinking }: { markdown: string; thinking: string }) {
  const [showThinking, setShowThinking] = useState(false);
  return (
    <div className="rounded-3xl bg-surface border hairline shadow-card overflow-hidden">
      <div className="flex items-center justify-between px-7 py-4 border-b hairline">
        <div className="flex items-baseline gap-3">
          <span className="font-display text-[20px] font-semibold text-oxblood">Opus 4.7 synthesis</span>
          <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted">adaptive thinking · cached prefix</span>
        </div>
        {thinking && (
          <button
            onClick={() => setShowThinking((s) => !s)}
            className="text-[12px] font-mono text-muted hover:text-oxblood transition"
          >
            {showThinking ? "hide" : "show"} model reasoning
          </button>
        )}
      </div>

      <AnimatePresence initial={false}>
        {showThinking && thinking && (
          <motion.div
            initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-b hairline bg-bg/40"
          >
            <pre className="px-7 py-4 text-[12px] text-ink2 whitespace-pre-wrap font-mono leading-relaxed max-h-[280px] overflow-y-auto">
              {thinking}
            </pre>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="px-7 py-6 prose-clinical">
        {markdown.trim().length > 0 ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
        ) : (
          <p className="text-muted italic serif-italic">Waiting for Opus 4.7 to begin reasoning over the assembled evidence…</p>
        )}
      </div>
    </div>
  );
}
