# HepVar

**Hepatology rare-variant clinical intelligence — powered by Claude Opus 4.7.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.14+](https://img.shields.io/badge/Python-3.14+-blue.svg)](https://www.python.org)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org)
[![Built with Opus 4.7](https://img.shields.io/badge/Built%20with-Claude%20Opus%204.7-D77757.svg)](https://www.anthropic.com)

> A hepatologist receives a Brazilian patient's exome with a missense variant in *ABCB4*. The lab calls it *Variant of Uncertain Significance.* Square one.
>
> HepVar is the workflow you would otherwise run by hand to fix that — automated, auditable, and reframable for clinicians and patients without changing a single number underneath.

---

## Why HepVar exists

Five years ago, my wife was misdiagnosed with autoimmune hepatitis and put on lifelong immunosuppressants she never fully responded to. After four specialists and years of side effects, a fifth one finally suspected a rare genetic liver disease and ordered a genetic test. It came back with a missense variant in `ABCB4` — and a verdict from the lab that said *"we don't know."*

That answer came back not because the variant was harmless, but because most of the world's variant databases were curated from European-ancestry cohorts, and patients with Brazilian, Latin-American, or African ancestry are systematically under-represented. The signal was there — just scattered across functional studies, protein-structure predictions, regulatory tracks of liver-cell genome models, and case reports in non-English journals. Reconstructing it took my wife (a geneticist) and me (PhD, molecular biology) **weeks of manual bioinformatics work**. After it was assembled, the diagnosis flipped, the treatment changed, and her symptoms resolved in a month.

**Most families do not have two molecular-biology researchers at home. Most clinicians do not have hours to chase scattered genetic evidence.** HepVar is that workflow — automated.

---

## What HepVar does

Given a raw genomic variant `(chrom, pos, ref, alt)`, HepVar:

1. **Annotates** the variant with Ensembl VEP (HGVS, consequence, rsID, UniProt mapping).
2. **Queries 12 evidence sources** in parallel —
   - Population: **gnomAD v4** (with per-ancestry breakdown for equity highlighting)
   - Clinical curation: **ClinVar**
   - Protein knowledge: **UniProt** + **InterPro**
   - Structure: **AlphaFold-EBI** (reference fold) + **ESMFold** (variant fold) + **AlphaMissense** + ΔΔG estimation
   - Regulation: **AlphaGenome** (per-modality liver-cell-track deltas + splicing predictions)
   - Tissue context: **GTEx** + **Human Protein Atlas** + **Reactome** + **KEGG**
   - Cross-assembly: **GRCh37 ↔ GRCh38 liftover** (with wrong-assembly gene-overlap warnings)
   - Literature: **PubMed** + **Europe PMC** across English, Portuguese, Spanish, Italian, French
3. **Scores** the assembled evidence with the full **ACMG/AMP Tavtigian-Bayesian classifier** — the international standard geneticists use to classify rare variants.
4. **Synthesizes** with **Claude Opus 4.7** + extended thinking (`adaptive` type, `summarized` display). The model walks each ACMG criterion, resolves source-level conflicts, names the specific functional assay that would resolve a remaining VUS, and emits an auditable reasoning trace a clinician can read line-by-line and challenge.
5. **Reframes** the same numbers for three audiences — **technical / clinician / patient** — without re-running the pipeline. Opus rephrases; the science underneath does not change.
6. **Streams** every step over Server-Sent Events: pipeline progress, reasoning deltas, thinking deltas, chat replies. Follow-up questions reuse the cached evidence packet at ~one-tenth of the per-token cost of the original analysis.

The clinical output includes:

- A **verdict pill** (Pathogenic / Likely Pathogenic / VUS / Likely Benign / Benign) with posterior probability and the full ACMG criteria checklist with rationales.
- **Per-source evidence cards** — population frequency bar chart with equity highlight, AA-substitution physicochemistry, multi-transcript HGVS, strand explainer, gnomAD ancestry breakdown, disease-spectrum table per gene, sequence-context strip with annotated functional residues, per-modality AlphaGenome panel, structure card with 3Dmol.js viewer, and curated literature.
- An **EVIDENCE GAPS** section that names the next experiment.
- A **conversational chat** scoped to the report's evidence packet — clinician-mode, patient-mode, technical-mode tone all available.
- A **printable manuscript-style PDF** of the full report.

---

## Architecture

```
                    Variant (chrom, pos, ref, alt)
                                │
                                ▼
                        Ensembl VEP  ──────►  HGVS, consequence, rsID, UniProt ID
                                │
                                ▼  (parallel, async)
        ┌────────────────────────────────────────────────────────────┐
        │  gnomAD v4   ·   ClinVar   ·   UniProt   ·   InterPro       │
        │  AlphaFold-EBI  +  ESMFold  +  AlphaMissense  +  ΔΔG        │
        │  AlphaGenome  (liver-cell regulatory + splicing tracks)     │
        │  GTEx · Human Protein Atlas · Reactome · KEGG               │
        │  GRCh37 ↔ GRCh38 liftover                                   │
        │  PubMed + Europe PMC  (en, pt, es, it, fr)                  │
        └────────────────────────────────────────────────────────────┘
                                │
                                ▼
                  ACMG/AMP Tavtigian-Bayesian classifier
                                │
                                ▼
          Claude Opus 4.7  ─  extended thinking  ·  prompt caching
                                │
            ┌─────────┬─────────┼─────────┬─────────┐
            ▼         ▼         ▼         ▼         ▼
         VERDICT   EVIDENCE   CONFLICT  EVIDENCE   CLINICAL
                  SYNTHESIS  RESOLUTION   GAPS    RECOMMENDATION
                                │
                                ▼
       Streaming clinical dashboard  +  conversational follow-up
       (re-frameable for technical / clinician / patient audiences)
```

---

## Tech stack

| Layer        | Stack                                                                            |
|--------------|----------------------------------------------------------------------------------|
| Backend      | FastAPI · `httpx` async · `diskcache` · Pydantic v2                              |
| Reasoning    | `anthropic` SDK · Claude Opus 4.7 · adaptive thinking · prompt caching           |
| Frontend     | Next.js 15 App Router · React 19 · Tailwind CSS · Framer Motion · 3Dmol.js       |
| Streaming    | Server-Sent Events end-to-end (`sse-starlette`)                                  |
| PDF export   | WeasyPrint                                                                       |
| Caching      | `diskcache` (per-source TTL) + on-disk fixtures for offline demo mode            |

---

## Quickstart

### Prerequisites

- **Anthropic API key** — create at [console.anthropic.com](https://console.anthropic.com)
- **NCBI API key** — create at [account.ncbi.nlm.nih.gov](https://account.ncbi.nlm.nih.gov/settings/) for higher PubMed rate limits
- **AlphaGenome API key** — request research access via [Google AI Studio / DeepMind](https://deepmind.google/technologies/alphagenome/)
- Python 3.14+
- Node.js 20+

### Install and run

```bash
# Clone
git clone https://github.com/arielmmaia/hepvar.git
cd hepvar

# Backend
cp .env.example .env       # fill keys — or use the in-app setup wizard
cd backend
pip install -e .
uvicorn api.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                # http://localhost:3000
```

### In-app setup wizard (zero-config onboarding)

If `.env` is missing or any key is invalid, the landing page renders an **interactive setup wizard** instead of the variant input. The wizard's left pane is an Opus 4.7 chat that walks you through obtaining each key with provider-specific instructions and URLs. The right pane is the form where you paste each key.

**The chat path never receives the key values.** Keys are written to `.env` only by a separate non-LLM endpoint (`POST /api/setup/keys`) with strict isolation — the wizard system prompt is told *which providers are still missing* (provider names only) but never the values. If a user pastes a key into the chat by mistake, the model is hard-instructed to redirect them to the form.

### Demo mode (offline-reproducible)

```bash
HEPVAR_DEMO_MODE=1 uvicorn api.main:app --port 8000
```

In demo mode, the pipeline resolves every source from on-disk fixtures under `evidence/fixtures/<variant_key>/<source>.json` instead of hitting the network. Useful for screen recordings, reproducible test runs, or working without API keys for the upstream sources. **Opus synthesis and audience-mode translations still call live** (which is what you want on screen — the streaming reasoning is the demo).

The repo ships with fixtures pre-cached for several test variants, including the ABCB4 LPAC variant (`chr7:87408188 T>C`) used in the demo video.

---

## Demo variant

`chr7:87408188 T>C` — a missense variant in **ABCB4** (MDR3 phosphatidylcholine floppase), the canonical gene of low-phospholipid-associated cholelithiasis (LPAC) syndrome and progressive familial intrahepatic cholestasis type 3 (PFIC3).

HepVar's verdict on this variant: **Pathogenic** (ACMG/AMP Tavtigian-Bayesian).

A 3-minute demo video walks through the full analysis end-to-end. See [`DEMO.md`](DEMO.md) for the script.

---

## Audience modes

Every report can be re-framed without changing the underlying data. The toggle lives in the synthesis pane header.

| Mode        | Audience                       | What changes                                                                         |
|-------------|--------------------------------|--------------------------------------------------------------------------------------|
| Technical   | Bioinformaticians, geneticists | Default. ACMG codes, deltas, posteriors, criteria with rationales.                   |
| Clinician   | Hepatology consultants         | Foreground action. Keep ACMG vocabulary; cut bioinformatics jargon. Plain enough that a busy consultant can scan it.  |
| Patient     | Patients, family members       | Plain language. Every technical term defined inline. No ACMG codes, no probability values, ends with questions to ask the doctor. |

Translations are computed on demand and cached server-side per `(jobId, mode)` plus client-side per session — first click re-frames in ~5 s; every subsequent click on the same mode is instant.

The variant-under-interpretation header, the ACMG verdict pill, and the ACMG criteria checklist remain in technical form across all modes. Those are audit-trail elements a clinician needs unchanged regardless of who else is reading the rest of the report.

---

## Notable engineering details

- **Adaptive thinking display**: `thinking={"type":"adaptive","display":"summarized"}` so the deliberation is human-readable in the UI.
- **Prompt caching**: ACMG instruction set + structured evidence packet are written to cache once via `cache_control: {type:"ephemeral"}`. Conversational follow-ups read at ~1/10th the per-token cost.
- **Pipeline parallelism**: VEP gates the rest; everything downstream runs under a single `asyncio.gather`.
- **Graceful degradation**: every source flags `confidence: missing` if it can't reach data, and Opus 4.7 is instructed to call out those gaps explicitly in CONFLICT RESOLUTION rather than confabulate.
- **SSE resume**: streams use `Last-Event-ID` so a flaky connection re-attaches without replaying every event.
- **Equity highlighting**: gnomAD per-ancestry frequencies are surfaced in their own card so under-representation is visible at a glance.
- **Structure viewer**: 3Dmol.js panel renders both the AlphaFold reference and the ESMFold variant, with per-residue pLDDT highlighted at the variant position.

---

## Hackathon

Built solo for the Cerebral Valley **"Built with Opus 4.7"** virtual hackathon (April 21–26, 2026).

- Submission details: [`SUBMISSION-FORM.md`](SUBMISSION-FORM.md)
- 3-minute demo script: [`DEMO.md`](DEMO.md)
- Engineering runbook: [`RUNBOOK.md`](RUNBOOK.md)

Track: **Build From What You Know.**

---

## Citations

- **ACMG/AMP variant classification** — Richards S, Aziz N, Bale S, et al. *Standards and guidelines for the interpretation of sequence variants...* Genet Med. 2015;17(5):405–424.
- **Tavtigian Bayesian framework** — Tavtigian SV, Greenblatt MS, Harrison SM, et al. *Modeling the ACMG/AMP variant classification guidelines as a Bayesian classification framework.* Genet Med. 2018;20(9):1054–1060.
- **AlphaFold** — Jumper J, Evans R, Pritzel A, et al. *Highly accurate protein structure prediction with AlphaFold.* Nature. 2021;596(7873):583–589.
- **AlphaMissense** — Cheng J, Novati G, Pan J, et al. *Accurate proteome-wide missense variant effect prediction with AlphaMissense.* Science. 2023;381(6664):eadg7492.
- **AlphaGenome** — DeepMind, 2024 (research access).
- **gnomAD v4** — Karczewski KJ, et al. *The mutational constraint spectrum quantified from variation in 141,456 humans.* Nature. 2020.
- **Ensembl VEP** — McLaren W, et al. *The Ensembl Variant Effect Predictor.* Genome Biol. 2016;17:122.
- **ABCB4 / LPAC syndrome** — Rosmorduc O, Hermelin B, Poupon R. *MDR3 gene defect in adults with symptomatic intrahepatic and gallbladder cholesterol cholelithiasis.* Gastroenterology. 2001;120(6):1459–1467.

---

## License

MIT — see [`LICENSE`](LICENSE).

---

## Author

**Ariel Maia** — Postdoc researcher, PhD in Cellular and Molecular Biology
CPBMF / INCT-TB, Pontifical Catholic University of Rio Grande do Sul (PUCRS), Porto Alegre, Brazil
GitHub: [@arielmmaia](https://github.com/arielmmaia)

---

> **Disclaimer.** HepVar is a research and educational tool for variant interpretation. It is not a medical device, does not provide a diagnosis, and is not a substitute for professional clinical judgement. Any clinical use requires independent confirmation by a qualified geneticist or clinician, and any classification HepVar produces should be treated as a hypothesis to be tested with orthogonal evidence — including, where indicated, a functional assay or family co-segregation study.
