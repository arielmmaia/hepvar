"use client";
import { useState } from "react";
import clsx from "clsx";
import { saveKey, type Provider, type ProviderStatus } from "@/lib/setup";

interface Meta {
  label: string;
  helpUrl: string;
  helpName: string;
  placeholder: string;
}

const PROVIDER_META: Record<Provider, Meta> = {
  anthropic: {
    label: "Anthropic API key",
    helpUrl: "https://console.anthropic.com",
    helpName: "Anthropic Console → Settings → API Keys",
    placeholder: "sk-ant-api03-…",
  },
  ncbi: {
    label: "NCBI API key",
    helpUrl: "https://account.ncbi.nlm.nih.gov",
    helpName: "NCBI Account Settings → API Key Management",
    placeholder: "long alphanumeric (no prefix)",
  },
  alphagenome: {
    label: "AlphaGenome API key",
    helpUrl: "https://aistudio.google.com/app/apikey",
    helpName: "Google AI Studio → API key (+ AlphaGenome research access)",
    placeholder: "AIza…",
  },
};

export function KeyForm({
  provider,
  status,
  onChange,
}: {
  provider: Provider;
  status: ProviderStatus;
  onChange: () => void; // called after a successful save so parent can re-fetch status
}) {
  const meta = PROVIDER_META[provider];
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [reveal, setReveal] = useState(false);

  async function submit(e?: React.FormEvent) {
    e?.preventDefault();
    if (!value.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      const res = await saveKey(provider, value.trim());
      if (!res.ok) {
        setErr(res.error || "validation failed");
      } else {
        setValue("");
        onChange();
      }
    } catch (ex: any) {
      setErr(ex?.message || "request failed");
    } finally {
      setBusy(false);
    }
  }

  const ok = status === "configured";

  return (
    <div className={clsx("rounded-2xl border hairline px-5 py-4 transition", ok ? "bg-leaf/5" : "bg-surface")}>
      <div className="flex items-baseline justify-between mb-1">
        <div className="flex items-center gap-2">
          {ok ? (
            <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-leaf text-surface text-[12px] font-bold">✓</span>
          ) : (
            <span className="inline-flex items-center justify-center w-5 h-5 rounded-full border border-hairline text-muted text-[11px]">·</span>
          )}
          <span className="font-display text-[16px] text-ink">{meta.label}</span>
        </div>
        <a
          href={meta.helpUrl}
          target="_blank"
          rel="noreferrer"
          className="text-[11px] font-mono text-muted hover:text-oxblood transition"
        >
          {meta.helpName} ↗
        </a>
      </div>

      {ok ? (
        <p className="text-[12px] text-muted italic serif-italic">
          configured & validated.{" "}
          <button onClick={() => onChange()} className="underline hover:text-oxblood">
            re-test
          </button>
        </p>
      ) : (
        <form onSubmit={submit} className="flex gap-2 items-stretch mt-1">
          <input
            type={reveal ? "text" : "password"}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={meta.placeholder}
            disabled={busy}
            autoComplete="off"
            spellCheck={false}
            className="flex-1 rounded-lg border hairline bg-bg/40 px-3 py-2 font-mono text-[13px] text-ink focus:border-oxblood focus:outline-none"
          />
          <button
            type="button"
            onClick={() => setReveal((r) => !r)}
            disabled={busy}
            className="rounded-lg border hairline bg-surface px-2 text-[11px] text-muted hover:text-oxblood transition"
          >
            {reveal ? "hide" : "show"}
          </button>
          <button
            type="submit"
            disabled={busy || !value.trim()}
            className="rounded-lg bg-oxblood text-surface px-4 text-[13px] disabled:opacity-50 transition"
          >
            {busy ? "…" : "validate"}
          </button>
        </form>
      )}
      {err && <p className="mt-2 text-[12px] text-coral">{err}</p>}
    </div>
  );
}
