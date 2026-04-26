// Audience-mode storage, hooks, and translate-endpoint client.

import { useEffect, useState, useCallback } from "react";

export type AudienceMode = "technical" | "clinician" | "patient";
const KEY = "hepvar.audience";
const DEFAULT: AudienceMode = "technical";

export function getAudience(): AudienceMode {
  if (typeof window === "undefined") return DEFAULT;
  const v = window.localStorage.getItem(KEY);
  if (v === "technical" || v === "clinician" || v === "patient") return v;
  return DEFAULT;
}

export function setAudience(mode: AudienceMode): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, mode);
  // Notify same-tab listeners (storage event only fires for *other* tabs).
  window.dispatchEvent(new CustomEvent("hepvar:audience", { detail: mode }));
}

export function useAudience(): [AudienceMode, (m: AudienceMode) => void] {
  const [mode, setMode] = useState<AudienceMode>(DEFAULT);
  useEffect(() => {
    setMode(getAudience());
    const onChange = () => setMode(getAudience());
    window.addEventListener("hepvar:audience", onChange as EventListener);
    window.addEventListener("storage", onChange);
    return () => {
      window.removeEventListener("hepvar:audience", onChange as EventListener);
      window.removeEventListener("storage", onChange);
    };
  }, []);
  const update = useCallback((m: AudienceMode) => setAudience(m), []);
  return [mode, update];
}

// ----- translate endpoint client -----

const API_BASE =
  (typeof window !== "undefined" && (window as any).__HEPVAR_API__) ||
  process.env.NEXT_PUBLIC_API_BASE ||
  "http://localhost:8000";

export interface TranslateRequest {
  target: "synthesis" | "card";
  mode: "clinician" | "patient";
  card?: string;
}

export async function streamTranslate(
  jobId: string,
  req: TranslateRequest,
  onDelta: (text: string) => void,
  onDone: () => void,
): Promise<void> {
  const r = await fetch(`${API_BASE}/api/jobs/${jobId}/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!r.ok || !r.body) {
    onDone();
    return;
  }
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
        if (ev.type === "text_delta") onDelta(ev.text);
        else if (ev.type === "text_done") {
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

// In-tab cache so re-renders don't re-fetch the same translation.
const _memCache = new Map<string, string>();

function _key(jobId: string, target: string, mode: string, card?: string) {
  return `${jobId}:${target}:${mode}:${card ?? ""}`;
}

/**
 * useTranslated — hook that lazily fetches a translation when (jobId, target, mode, card)
 * indicates a non-technical mode. Returns {text, loading, error}. Returns text="" for
 * technical mode (caller falls back to the original technical content).
 */
export function useTranslated(
  jobId: string | null,
  target: "synthesis" | "card",
  mode: AudienceMode,
  card?: string,
  enabled: boolean = true,
): { text: string; loading: boolean; error: string | null } {
  const [text, setText] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setText("");
    setError(null);
    if (!enabled || !jobId || mode === "technical") {
      setLoading(false);
      return;
    }
    const cacheKey = _key(jobId, target, mode, card);
    const cached = _memCache.get(cacheKey);
    if (cached) {
      setText(cached);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    let buf = "";
    streamTranslate(
      jobId,
      { target, mode: mode as "clinician" | "patient", card },
      (delta) => {
        if (cancelled) return;
        buf += delta;
        setText(buf);
      },
      () => {
        if (cancelled) return;
        _memCache.set(cacheKey, buf);
        setLoading(false);
      },
    ).catch((e: any) => {
      if (cancelled) return;
      setError(e?.message || "translate failed");
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [jobId, target, mode, card, enabled]);

  return { text, loading, error };
}
