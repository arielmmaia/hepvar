import type { Report, StreamEvent, VariantInput, ChatEvent } from "./types";

export async function startAnalysis(v: VariantInput): Promise<{ jobId: string }> {
  const r = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(v),
  });
  if (!r.ok) throw new Error(`/analyze failed: ${r.status}`);
  const j = (await r.json()) as { jobId: string };
  return j;
}

export function streamJob(jobId: string, onEvent: (e: StreamEvent) => void): () => void {
  const es = new EventSource(`/api/jobs/${jobId}/stream`);
  es.onmessage = (m) => {
    if (!m.data) return;
    try {
      const ev = JSON.parse(m.data) as StreamEvent;
      onEvent(ev);
      if (ev.type === "done" || ev.type === "error") es.close();
    } catch {
      /* ignore malformed */
    }
  };
  es.onerror = () => {
    /* SSE auto-reconnects unless closed; leave it. */
  };
  return () => es.close();
}

export async function getReport(jobId: string): Promise<Report> {
  const r = await fetch(`/api/jobs/${jobId}/report`);
  if (!r.ok) throw new Error(`/report failed: ${r.status}`);
  return (await r.json()) as Report;
}

export async function streamChat(
  jobId: string,
  history: { role: string; content: string }[],
  question: string,
  onDelta: (text: string) => void,
  onDone: () => void,
): Promise<void> {
  const r = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jobId, history, question }),
  });
  if (!r.ok || !r.body) throw new Error(`/chat failed: ${r.status}`);
  const reader = r.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";
    for (const part of parts) {
      const dataLine = part.split("\n").find((l) => l.startsWith("data:"));
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
