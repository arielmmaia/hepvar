"use client";
import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { streamSetupChat } from "@/lib/setup";

interface Msg { role: "user" | "assistant"; content: string }

export interface ParsedReady {
  mode?: "technical" | "clinician" | "patient";
  variant?: { chrom: string; pos: number; ref: string; alt: string };
}

// Detect "READY: mode=clinician, variant=chr7:87408188 T>C" line in the latest assistant text.
export function parseReadyLine(text: string): ParsedReady | null {
  const m = text.match(/READY:\s*mode=(technical|clinician|patient)\s*,\s*variant=(chr[\dXYM]+):(\d+)\s+([ACGTacgt]+)\s*>\s*([ACGTacgt]+)/i);
  if (!m) return null;
  return {
    mode: m[1].toLowerCase() as any,
    variant: {
      chrom: m[2],
      pos: parseInt(m[3], 10),
      ref: m[4].toUpperCase(),
      alt: m[5].toUpperCase(),
    },
  };
}

export function SetupChat({
  enabled,
  onReady,
}: {
  enabled: boolean;
  onReady?: (ready: ParsedReady) => void;
}) {
  const [history, setHistory] = useState<Msg[]>([]);
  const [draft, setDraft] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [partial, setPartial] = useState("");
  const [autoStarted, setAutoStarted] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // When enabled flips true, fire an opening turn so the user gets greeted.
  useEffect(() => {
    if (enabled && !autoStarted) {
      setAutoStarted(true);
      void send("Hi — I just enabled my Anthropic key. Where do we go from here?");
    }
  }, [enabled, autoStarted]);

  // Auto-scroll on new content
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [history, partial]);

  async function send(question: string) {
    if (!question.trim() || streaming || !enabled) return;
    setStreaming(true);
    setPartial("");
    const newHist: Msg[] = [...history, { role: "user", content: question }];
    setHistory(newHist);
    setDraft("");
    let buf = "";
    try {
      await streamSetupChat(history, question,
        (delta) => { buf += delta; setPartial(buf); },
        () => {
          setHistory([...newHist, { role: "assistant", content: buf }]);
          setPartial("");
          setStreaming(false);
          const ready = parseReadyLine(buf);
          if (ready && onReady) onReady(ready);
        },
      );
    } catch {
      setStreaming(false);
    }
  }

  return (
    <div className="rounded-3xl bg-surface border hairline shadow-card flex flex-col h-full overflow-hidden">
      <div className="px-5 py-3 border-b hairline flex items-baseline justify-between">
        <span className="font-display text-[17px] font-semibold text-ink">Setup assistant</span>
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">opus 4.7 · keys never seen</span>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-4 max-h-[440px]">
        {!enabled && (
          <div className="text-[13px] text-muted italic serif-italic">
            Add your Anthropic API key on the right to wake the setup assistant.
          </div>
        )}
        {enabled && history.length === 0 && !partial && (
          <div className="text-[13px] text-muted italic serif-italic">
            Connecting…
          </div>
        )}
        {history.map((m, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}>
            {m.role === "user" ? (
              <div className="ml-auto max-w-[88%] bg-oxblood text-surface rounded-2xl rounded-br-sm px-4 py-2.5 text-[14px] whitespace-pre-wrap">
                {m.content}
              </div>
            ) : (
              <div className="mr-auto max-w-[92%] text-[14px] text-ink2 leading-relaxed prose-clinical">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
              </div>
            )}
          </motion.div>
        ))}
        {streaming && (
          <div className="text-[14px] text-ink2 leading-relaxed prose-clinical">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{partial || ""}</ReactMarkdown>
            <span className="inline-block w-2 h-4 bg-oxblood dot-pulse align-baseline" />
          </div>
        )}
      </div>
      <form
        onSubmit={(e) => { e.preventDefault(); send(draft); }}
        className="border-t hairline px-3 py-3 flex gap-2 items-stretch"
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={enabled ? "Ask the setup assistant…" : "Locked — add Anthropic key first"}
          disabled={!enabled || streaming}
          className="flex-1 rounded-xl border hairline bg-bg/40 px-3 py-2 text-[14px] focus:border-oxblood focus:outline-none"
        />
        <button
          type="submit"
          disabled={!enabled || streaming || !draft.trim()}
          className="rounded-xl bg-oxblood text-surface px-4 py-2 text-[14px] disabled:opacity-50 transition"
        >
          send
        </button>
      </form>
    </div>
  );
}
