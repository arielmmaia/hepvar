import type { Report, StreamEvent, VariantInput, ChatEvent } from "./types";

// Talk directly to the FastAPI backend (CORS is wired in main.py).
// The Next.js rewrite() proxy buffers SSE in dev so we bypass it.
const API_BASE =
  (typeof window !== "undefined" && (window as any).__HEPVAR_API__) ||
  process.env.NEXT_PUBLIC_API_BASE ||
  "http://localhost:8000";

export async function startAnalysis(v: VariantInput): Promise<{ jobId: string }> {
  const r = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(v),
  });
  if (!r.ok) throw new Error(`/analyze failed: ${r.status}`);
  const j = (await r.json()) as { jobId: string };
  return j;
}

export function streamJob(jobId: string, onEvent: (e: StreamEvent) => void): () => void {
  const es = new EventSource(`${API_BASE}/api/jobs/${jobId}/stream`);
  // Defensive dedup: even though the backend uses Last-Event-ID for clean
  // resume, if the browser EventSource ever re-delivers an id we've already
  // processed (it shouldn't, but safety first), drop the duplicate.
  const seen = new Set<string>();
  es.onmessage = (m) => {
    if (!m.data) return;
    if (m.lastEventId && seen.has(m.lastEventId)) return;
    if (m.lastEventId) seen.add(m.lastEventId);
    try {
      const ev = JSON.parse(m.data) as StreamEvent;
      onEvent(ev);
      if (ev.type === "done" || ev.type === "error") es.close();
    } catch {
      /* ignore malformed */
    }
  };
  es.onerror = () => {
    /* SSE auto-reconnects unless closed. With Last-Event-ID set on the
       browser side and respected on the backend, the new connection
       resumes past the last-seen event instead of replaying from 0. */
  };
  return () => es.close();
}

export async function getReport(jobId: string): Promise<Report> {
  const r = await fetch(`${API_BASE}/api/jobs/${jobId}/report`);
  if (!r.ok) throw new Error(`/report failed: ${r.status}`);
  return (await r.json()) as Report;
}

export async function streamChat(
  jobId: string,
  history: { role: string; content: string }[],
  question: string,
  mode: "technical" | "clinician" | "patient",
  onDelta: (text: string) => void,
  onDone: () => void,
): Promise<void> {
  const r = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jobId, history, question, mode }),
  });
  if (!r.ok || !r.body) throw new Error(`/chat failed: ${r.status}`);
  const reader = r.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  // sse-starlette emits events terminated by CRLF-CRLF, not LF-LF — splitting on
  // \n\n alone never finds a complete event and the chat appears to "do nothing".
  const eventSep = /\r?\n\r?\n/;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const parts = buf.split(eventSep);
    buf = parts.pop() ?? "";
    for (const part of parts) {
      const dataLine = part.split(/\r?\n/).find((l) => l.startsWith("data:"));
      if (!dataLine) continue;
      const json = dataLine.slice(5).trim();
      if (!json) continue;
      try {
        const ev = JSON.parse(json) as ChatEvent;
        if (ev.type === "chat_delta") onDelta(ev.text);
        else if (ev.type === "chat_done") {
          onDone();
          return;
        }
      } catch {
        /* ignore */
      }
    }
  }
  onDone();
}
