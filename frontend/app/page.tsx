"use client";
import { useEffect, useState } from "react";
import { VariantInput } from "@/components/VariantInput";
import { SetupWizard } from "@/components/SetupWizard";
import { getSetupStatus, type SetupStatus } from "@/lib/setup";

export default function Home() {
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [forceLanding, setForceLanding] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await getSetupStatus();
        if (!cancelled) setStatus(s);
      } catch {
        if (!cancelled) setStatus({ anthropic: "missing", ncbi: "missing", alphagenome: "missing", all_ready: false });
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (status === null) {
    return (
      <main className="max-w-[1180px] mx-auto px-6 md:px-10 pt-32 text-center text-muted font-mono text-[12px] uppercase tracking-[0.25em]">
        loading…
      </main>
    );
  }

  if (!status.all_ready && !forceLanding) {
    return <SetupWizard initialStatus={status} onComplete={() => setForceLanding(true)} />;
  }

  return (
    <main className="max-w-[1180px] mx-auto px-6 md:px-10 pt-12 md:pt-20 pb-24">
      <header className="flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <span className="font-display text-2xl tracking-tightest font-semibold text-oxblood">HepVar</span>
          <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-muted">v0.1 · opus 4.7</span>
        </div>
        <nav className="flex items-center gap-6 text-[13px] text-ink2">
          <button onClick={() => setForceLanding(false)} className="hover:text-oxblood transition font-mono text-[12px] uppercase tracking-[0.18em] text-muted">
            reconfigure keys
          </button>
          <a className="hover:text-oxblood transition" href="https://github.com" target="_blank" rel="noreferrer">github</a>
          <a className="hover:text-oxblood transition" href="#about">about</a>
        </nav>
      </header>

      <section className="mt-16 md:mt-24 grid md:grid-cols-12 gap-10 items-end">
        <div className="md:col-span-8">
          <h1 className="font-display font-light text-[56px] md:text-[88px] leading-[0.95] tracking-tightest text-ink">
            <span>The clinician's</span><br/>
            <span className="serif-italic text-oxblood">interpretation layer</span><br/>
            <span>for rare liver disease.</span>
          </h1>
          <p className="mt-7 max-w-[58ch] text-[17px] leading-relaxed text-ink2">
            A Brazilian patient's exome comes back with a missense in <span className="font-mono">ABCB4</span>.
            The sequencing report says <em className="serif-italic">"variant of uncertain significance — no link to disease established."</em>
            HepVar reasons over gnomAD, ClinVar, AlphaFold, AlphaGenome, AlphaMissense, and multilingual
            case literature with <strong className="text-oxblood">Claude Opus 4.7</strong> to give the
            hepatologist an answer — and to say exactly which assay would resolve a residual VUS.
          </p>
        </div>
        <div className="md:col-span-4 text-right">
          <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-muted mb-2">Built for the</p>
          <p className="font-display text-2xl text-ink leading-tight">Built with Opus 4.7<br/>Cerebral Valley Hackathon<br/><span className="text-muted text-base">April 21–26, 2026</span></p>
        </div>
      </section>

      <div className="mt-14">
        <VariantInput />
      </div>

      <section id="about" className="mt-24 grid md:grid-cols-3 gap-8 text-[15px] leading-relaxed">
        <Pillar
          eyebrow="Equity"
          title="In-silico tools as the equalizer"
          body="ClinVar, OMIM, and most variant literature are Eurocentric. AlphaGenome, AlphaFold, ESMFold, and AlphaMissense provide ancestry-neutral evidence that compensates for missing population data — the central methodological premise."
        />
        <Pillar
          eyebrow="Multilingual"
          title="The Portuguese case report no curator submitted"
          body="A meaningful fraction of rare hepatology variant evidence lives only in Portuguese, Spanish, Italian, and French regional journals never submitted to ClinVar. Opus 4.7 reads them in original language and synthesises them into the clinical decision."
        />
        <Pillar
          eyebrow="Meta-cognition"
          title="What test would resolve this VUS?"
          body="The most clinically actionable output for a VUS is not just a label — it is a prescriptive recommendation. HepVar names the functional assay, family co-segregation study, or population cohort that would push the variant to LP or LB."
        />
      </section>

      <footer className="mt-24 border-t hairline pt-6 text-[12px] text-muted flex justify-between">
        <span>MIT licensed · Built solo, April 25–26 2026 · Ariel Maia · CPBMF / INCT-TB · Porto Alegre, Brazil</span>
        <span className="font-mono">claude-opus-4-7 · adaptive thinking · prompt caching</span>
      </footer>
    </main>
  );
}

function Pillar({ eyebrow, title, body }: { eyebrow: string; title: string; body: string }) {
  return (
    <div className="border-t-2 border-oxblood pt-5">
      <p className="text-[11px] uppercase tracking-[0.25em] text-oxblood font-mono">{eyebrow}</p>
      <h3 className="mt-2 font-display text-[22px] leading-tight text-ink">{title}</h3>
      <p className="mt-3 text-ink2">{body}</p>
    </div>
  );
}
