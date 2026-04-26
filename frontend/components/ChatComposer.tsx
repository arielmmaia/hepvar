"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { streamChat } from "@/lib/api";

interface Msg { role: "user" | "assistant"; content: string }

const SUGGESTIONS = [
  "Why was PM2 applied here?",
  "What functional assay would resolve the VUS?",
  "Could a Brazilian-ancestry founder effect explain the gnomAD absence?",
  "What surveillance interval do you recommend for the family?",
];

export function ChatComposer({ jobId, ready }: { jobId: string; ready: boolean }) {
  const [history, setHistory] = useState<Msg[]>([]);
  const [draft, setDraft] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [partial, setPartial] = useState("");

  async function send(question: string) {
    if (!question.trim() || streaming || !ready) return;
    setStreaming(true);
    setPartial("");
    const newHist: Msg[] = [...history, { role: "user", content: question }];
    setHistory(newHist);
    setDraft("");
    let buf = "";
    try {
      await streamChat(jobId, history, question,
        (delta) => { buf += delta; setPartial(buf); },
        () => {
          setHistory([...newHist, { role: "assistant", content: buf }]);
          setPartial("");
          setStreaming(false);
        },
      );
    } catch (e) {
      setStreaming(false);
    }
  }

  return (
    <div className="rounded-3xl bg-surface border hairline shadow-card overflow-hidden flex flex-col h-full">
      <div className="px-6 py-4 border-b hairline flex items-baseline justify-between">
        <span className="font-display text-[18px] font-semibold text-ink">Ask the model</span>
        <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted">~95% prompt cache reuse</span>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4 max-h-[440px]">
        {history.length === 0 && partial.length === 0 && (
          <div>
            <p className="text-[13px] text-muted italic serif-italic mb-3">
              Follow-ups stream from Opus 4.7 with the entire ACMG instruction set + evidence packet prompt-cached.
            </p>
            <ul className="space-y-2">
              {SUGGESTIONS.map((s) => (
                <li key={s}>
                  <button
                    disabled={!ready || streaming}
                    onClick={() => send(s)}
                    className="text-left text-[13px] text-ink2 italic serif-italic hover:text-oxblood transition disabled:opacity-50"
                  >
                    → {s}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        {history.map((m, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}>
            {m.role === "user" ? (
              <div className="ml-auto max-w-[88%] bg-oxblood text-surface rounded-2xl rounded-br-sm px-4 py-2.5 text-[14px]">
                {m.content}
              </div>
            ) : (
              <div className="mr-auto max-w-[92%] text-[14px] text-ink2 leading-relaxed whitespace-pre-wrap">
                {m.content}
              </div>
            )}
          </motion.div>
        ))}
        {streaming && (
          <div className="text-[14px] text-ink2 leading-relaxed whitespace-pre-wrap">
            {partial}
            <span className="ml-1 inline-block w-2 h-4 bg-oxblood dot-pulse align-baseline" />
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => { e.preventDefault(); send(draft); }}
        className="border-t hairline px-4 py-3 flex gap-2 items-stretch"
      >
        <input
          value={draft} onChange={(e) => setDraft(e.target.value)}
          placeholder={ready ? "Ask about the report…" : "Waiting for synthesis…"}
          disabled={!ready || streaming}
          className="flex-1 rounded-xl border hairline bg-bg/40 px-3 py-2 text-[14px] focus:border-oxblood focus:outline-none"
        />
        <button
          type="submit" disabled={!ready || streaming || !draft.trim()}
          className="rounded-xl bg-oxblood text-surface px-4 py-2 text-[14px] disabled:opacity-50 transition"
        >
          send
        </button>
      </form>
    </div>
  );
}
