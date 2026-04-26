# HepVar — Hepatology Rare-Variant Clinical Intelligence

> A clinician-facing variant interpretation tool for rare liver disease, powered by **Claude Opus 4.7**.

**Built during the Cerebral Valley "Built with Opus 4.7" hackathon (April 21–26, 2026).**

## Why HepVar exists

A hepatologist receiving a Brazilian patient's exome report sees a missense variant in `ABCB4`, the LPAC/PFIC3 gene. The sequencing company's report calls it **"variant of uncertain significance — no link to disease established."** The patient has progressive cholestasis. The clinician needs an answer.

The reason that report came back inconclusive is not that the variant is benign — it is that:

1. **ClinVar, OMIM and most curated databases are Eurocentric.** Variants common in Latin-American, African, or Asian-ancestry populations are systematically under-represented. gnomAD's `amr` cohort is a fraction of `nfe`.
2. **The relevant case report was published in Portuguese**, in a regional gastroenterology journal, never submitted to ClinVar curation.
3. **Cheaper sequencing means more rare variants surface every day** than human curators can keep up with.

HepVar closes this gap. Given a raw genomic variant (`chrom`, `pos`, `ref`, `alt`), it:

- annotates with Ensembl VEP and queries gnomAD, ClinVar, UniProt, InterPro, LOVD;
- runs a **multilingual** PubMed + EuropePMC search across English, Portuguese, Spanish, Italian and French;
- folds the reference protein from AlphaFold-EBI and the variant via ESMFold; computes RMSD, AlphaMissense, ΔΔG;
- queries **AlphaGenome** for liver-cell-track regulatory and splicing impact;
- enriches with hepatocyte-specific GTEx / Human Protein Atlas / Reactome / KEGG context;
- applies the full ACMG/AMP Tavtigian-Bayesian scoring framework;
- and finally hands the entire structured evidence object to **Claude Opus 4.7 with extended thinking**, which:
  - resolves conflicts across sources at differing confidence levels,
  - reads the Portuguese / Spanish / Italian / French case reports in their original language,
  - emits an **evidence-gap meta-cognition** section explaining exactly which functional assay or family co-segregation study would resolve a remaining VUS to LP/LB,
  - and answers conversational follow-ups in real time, with the entire ACMG instruction set + evidence object **prompt-cached** for ~95% token reuse.

The bet: **in-silico tools, leveraged by a model that can reason over conflicting multi-modal evidence, are the great equalizer for under-represented patient populations.**

## Architecture

```
Variant (chrom, pos, ref, alt)
        │
        ▼
   Ensembl VEP ─────────► HGVS, consequence, rsID, UniProt
        │
        ▼ (parallel)
   ┌────────────────────────────────────────────────────┐
   │ gnomAD · ClinVar · UniProt · InterPro · LOVD       │
   │ PubMed + EuropePMC (en, pt, es, it, fr)            │
   │ AlphaGenome · AlphaFold + ESMFold + AlphaMissense  │
   │ GTEx · HPA · Reactome · KEGG · liver gene panel    │
   └────────────────────────────────────────────────────┘
        │
        ▼
   ACMG/AMP Tavtigian Bayesian classifier
        │
        ▼
   Opus 4.7 synthesis (extended thinking + prompt caching)
        │  ┌─ VERDICT
        │  ├─ EVIDENCE SYNTHESIS
        │  ├─ CONFLICT RESOLUTION
        │  ├─ EVIDENCE GAPS  (meta-cognition)
        │  └─ CLINICAL RECOMMENDATION
        ▼
   Streaming clinical dashboard + conversational follow-up
```

## Stack

- **Backend**: FastAPI · `httpx` async · `diskcache` · Pydantic v2 · `anthropic` SDK
- **Reasoning**: Claude Opus 4.7 with extended thinking + prompt caching
- **Frontend**: Next.js 15 · Tailwind · Framer Motion · 3Dmol.js
- **Streaming**: Server-Sent Events end-to-end (pipeline progress + reasoning deltas + thinking deltas)

## Run it

```bash
# 1. Backend
cp .env.example .env  # fill ANTHROPIC_API_KEY, NCBI_API_KEY, ALPHAGENOME_API_KEY
cd backend
pip install -e .
uvicorn api.main:app --reload --port 8000

# 2. Frontend (separate terminal)
cd frontend
npm install
npm run dev  # http://localhost:3000
```

For an offline demo with the canonical ABCB4 LPAC variant pre-cached:

```bash
HEPVAR_DEMO_MODE=1 uvicorn api.main:app --port 8000
```

Then enter `chr7 87408188 T C` on the dashboard.

## Demo variant

`chr7:87408188 T>C` — a missense variant in **ABCB4** (MDR3 phosphatidylcholine floppase), the canonical gene of low-phospholipid-associated cholelithiasis (LPAC) syndrome and PFIC3.

## License

MIT.

## Built by

Ariel Maia (`@arielmmaia`) — postdoc, CPBMF / INCT-TB, PUCRS, Porto Alegre, Brazil.
Solo build, April 25–26 2026.
