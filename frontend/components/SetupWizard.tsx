"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { getSetupStatus, type SetupStatus, type Provider } from "@/lib/setup";
import { startAnalysis } from "@/lib/api";
import { setAudience, type AudienceMode } from "@/lib/audience";
import { KeyForm } from "./KeyForm";
import { SetupChat, type ParsedReady } from "./SetupChat";

const ALL_PROVIDERS: Provider[] = ["anthropic", "ncbi", "alphagenome"];

export function SetupWizard({ initialStatus, onComplete }: { initialStatus: SetupStatus; onComplete?: () => void }) {
  const router = useRouter();
  const [status, setStatus] = useState<SetupStatus>(initialStatus);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const refresh = async () => {
    try {
      setStatus(await getSetupStatus());
    } catch {
      /* ignore */
    }
  };

  // Refresh when window regains focus (in case user navigated to a key page and came back).
  useEffect(() => {
    const onFocus = () => void refresh();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  async function handleReady(ready: ParsedReady) {
    if (!ready.variant) return;
    setBusy(true);
    setErr(null);
    try {
      if (ready.mode) setAudience(ready.mode as AudienceMode);
      const v = { ...ready.variant, assembly: "GRCh38" as const };
      const { jobId } = await startAnalysis(v);
      router.push(`/analyze/${jobId}`);
    } catch (e: any) {
      setErr(e?.message || "failed to start analysis");
      setBusy(false);
    }
  }

  const anthropicReady = status.anthropic === "configured";

  return (
    <main className="max-w-[1180px] mx-auto px-6 md:px-10 pt-12 md:pt-16 pb-24">
      <header className="flex items-center justify-between mb-10">
        <div className="flex items-baseline gap-3">
          <span className="font-display text-2xl tracking-tightest font-semibold text-oxblood">HepVar</span>
          <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-muted">first-time setup</span>
        </div>
        {status.all_ready && onComplete && (
          <button onClick={onComplete} className="text-[12px] font-mono text-muted hover:text-oxblood">skip · I have all keys ↗</button>
        )}
      </header>

      <motion.section initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <h1 className="font-display text-[44px] md:text-[56px] leading-[1.0] tracking-tightest text-ink mb-3">
          Welcome — let's get your <span className="serif-italic text-oxblood">three keys</span> set.
        </h1>
        <p className="max-w-[64ch] text-[15px] leading-relaxed text-ink2">
          HepVar needs three free API keys to call Anthropic Claude (the brain), NCBI (ClinVar + PubMed),
          and Google AI Studio (AlphaGenome). The assistant on the left will walk you through getting each
          one. <strong>The assistant never sees the actual key values</strong> — keys go from the form on
          the right straight to the local <span className="font-mono">.env</span> file on this machine.
        </p>
      </motion.section>

      <div className="grid lg:grid-cols-2 gap-5 mt-10 items-start">
        <div className="lg:sticky lg:top-4">
          <SetupChat enabled={anthropicReady} onReady={handleReady} />
          {busy && (
            <p className="mt-3 text-[12px] text-muted italic serif-italic">Starting analysis…</p>
          )}
          {err && <p className="mt-3 text-[12px] text-coral">{err}</p>}
        </div>

        <div className="space-y-3">
          {ALL_PROVIDERS.map((p) => (
            <KeyForm key={p} provider={p} status={status[p]} onChange={refresh} />
          ))}

          <div className="rounded-2xl bg-bg/40 border hairline px-5 py-4 mt-2 text-[12px] text-muted">
            <p className="leading-relaxed">
              <strong className="text-oxblood font-mono uppercase tracking-[0.18em] text-[10px]">key isolation:</strong> the
              setup assistant on the left is powered by Claude Opus 4.7, but it only ever knows{" "}
              <em>which</em> providers are still missing — never the actual key values. Keys you paste
              into the fields above are sent directly to the local backend (POST /api/setup/keys),
              which validates against the provider and writes to <span className="font-mono">.env</span>.
              The assistant cannot read the file.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
