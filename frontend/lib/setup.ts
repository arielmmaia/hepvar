// Typed wrappers around the setup endpoints.

const API_BASE =
  (typeof window !== "undefined" && (window as any).__HEPVAR_API__) ||
  process.env.NEXT_PUBLIC_API_BASE ||
  "http://localhost:8000";

export type Provider = "anthropic" | "ncbi" | "alphagenome";
export type ProviderStatus = "missing" | "configured";

export interface SetupStatus {
  anthropic: ProviderStatus;
  ncbi: ProviderStatus;
  alphagenome: ProviderStatus;
  all_ready: boolean;
}

export interface SaveResponse {
  ok: boolean;
  provider: Provider;
  error?: string | null;
}

export async function getSetupStatus(): Promise<SetupStatus> {
  const r = await fetch(`${API_BASE}/api/setup/status`);
  if (!r.ok) throw new Error(`/api/setup/status failed: ${r.status}`);
  return (await r.json()) as SetupStatus;
}

export async function saveKey(provider: Provider, value: string): Promise<SaveResponse> {
  const r = await fetch(`${API_BASE}/api/setup/keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, value }),
  });
  if (!r.ok) {
    const text = await r.text();
    return { ok: false, provider, error: `HTTP ${r.status}: ${text.slice(0, 200)}` };
  }
  return (await r.json()) as SaveResponse;
}

export async function validateExistingKey(provider: Provider): Promise<SaveResponse> {
  const r = await fetch(`${API_BASE}/api/setup/validate/${provider}`, { method: "POST" });
  if (!r.ok) {
    const text = await r.text();
    return { ok: false, provider, error: `HTTP ${r.status}: ${text.slice(0, 200)}` };
  }
  return (await r.json()) as SaveResponse;
}

export async function streamSetupChat(
  history: { role: string; content: string }[],
  question: string,
  onDelta: (text: string) => void,
  onDone: () => void,
): Promise<void> {
  const r = await fetch(`${API_BASE}/api/setup/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ history, question }),
  });
  if (!r.ok || !r.body) throw new Error(`/api/setup/chat failed: ${r.status}`);
  const reader = r.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
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
        const ev = JSON.parse(json);
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
