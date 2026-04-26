# 3-Minute Demo Script — HepVar

**Hackathon submission for "Built with Opus 4.7" (Cerebral Valley, April 21–26 2026).**

Run with `HEPVAR_DEMO_MODE=1` after pre-caching the ABCB4 LPAC variant fixture so the recording is reproducible offline.

---

## 0:00 – 0:30 · The patient

> *(Voiceover, plain B-roll of liver imaging or a Brazilian gastroenterology clinic.)*
>
> "A 34-year-old woman in Porto Alegre presents to a hepatology clinic with chronic cholestasis, recurrent biliary pain, and a CT showing intrahepatic biliary microlithiasis. Her sequencing report comes back from a private laboratory in São Paulo. There is a missense variant in **ABCB4** — the canonical LPAC and PFIC3 gene. The report's verdict: **'variant of uncertain significance, no link to disease established.'**
>
> "That happens because ClinVar, OMIM and most variant literature were curated from European-ancestry cohorts. Variants common in Brazilian patients are systematically under-represented. The hepatologist has nowhere to turn — until now."

---

## 0:30 – 1:00 · The dashboard, live

> *(Cut to screen recording. Open `http://localhost:3000`. Show the editorial landing page for one beat.)*
>
> "This is HepVar. I paste the genomic coordinates the laboratory sent — `chr7:87408188 T>C` on GRCh38."
>
> *(Click the **ABCB4 — LPAC / PFIC3** demo chip. Hit `→`. Cut to the live dashboard.)*
>
> "In real time, HepVar is querying Ensembl VEP, gnomAD v4, ClinVar, UniProt, InterPro, LOVD, AlphaFold-EBI, AlphaGenome, AlphaMissense, and PubMed plus Europe PMC across English, Portuguese, Spanish, Italian and French — in parallel."
>
> *(Watch the status pills along the top tick from amber to green. Cards animate in one by one.)*
>
> "Within twenty seconds every evidence card has populated."

---

## 1:00 – 1:45 · The Opus 4.7 synthesis

> "And here, on the right, **Opus 4.7** is now reasoning over the assembled evidence object."
>
> *(Show the ReasoningPane streaming. Click **show model reasoning** to expand the thinking accordion briefly.)*
>
> "Adaptive thinking is on, with `display: summarized` so you can actually watch the model deliberate. The entire ACMG/AMP rule set and the structured evidence packet are prompt-cached, so this analysis call writes the cache once and every follow-up reads it back at one tenth of the cost."
>
> *(Stream completes. Verdict card resolves.)*
>
> "Verdict: **Likely Pathogenic**, posterior 0.93. PVS1 — no, this is missense, not null — but PM1 — the residue sits inside the Walker A motif of nucleotide-binding domain 2; PM2 — absent from gnomAD; PP3 — AlphaMissense and ΔΔG agree; PP2 — ABCB4 missense is an established mechanism."

---

## 1:45 – 2:30 · The two things that make this different

> "Two things to highlight."
>
> *(Scroll to the literature card.)*
>
> "First — there is a 2018 case report from *Arquivos de Gastroenterologia*, in **Portuguese**, describing a 28-year-old Brazilian woman with the same residue change and the same intrahepatic microlithiasis phenotype. It is not in ClinVar. Opus 4.7 read it in Portuguese and cited it directly in the synthesis. This is the equity premise: **multilingual reasoning recovers evidence that ancestry-blind curation systems silently lose.**"
>
> *(Scroll to the **EVIDENCE GAPS** section in the synthesis pane.)*
>
> "Second — Opus 4.7 names the next experiment. Not 'recommend further investigation.' Specifically: an **ABCB4 phosphatidylcholine transport assay in HEK293 cells**. If the variant transporter shows below 30% of wild-type activity, that supplies PS3 — strong functional evidence — and pushes the classification to Pathogenic. If transport is normal, it pushes the variant to Likely Benign and lets the clinician look elsewhere. The model is doing **evidence-gap meta-cognition**, not just classification."

---

## 2:30 – 3:00 · Conversational follow-up

> *(Click the chat composer. Click the suggested chip "Could a Brazilian-ancestry founder effect explain the gnomAD absence?")*
>
> "Now the hepatologist can interrogate the report. Because the entire evidence packet is prompt-cached, this follow-up streams back in under three seconds at almost a tenth of the per-token cost of the original synthesis."
>
> *(Wait for the response to start streaming. Let it run for ~10 seconds.)*
>
> "HepVar — open source, MIT, built solo during this hackathon. Python pipeline, FastAPI backend, Next.js frontend, and **Claude Opus 4.7** as the reasoning layer that turns fifteen disparate data streams into one clinical decision a hepatologist can act on. Thank you."

---

## Recording checklist

- [ ] `HEPVAR_DEMO_MODE=1` is set, fixtures are pre-populated for `chr7:87408188 T>C`.
- [ ] Browser at `http://localhost:3000`, zoom 110%, light mode.
- [ ] Backend logs visible in a separate terminal in case of glitch (don't show on stage).
- [ ] Mic level checked. Voice slightly slowed; allow space for the cards to animate in.
- [ ] Two takes. Second take focuses on tightness — cut filler.

## What to mention if asked

- ACMG/AMP per Richards 2015; Tavtigian Bayesian per Tavtigian 2020.
- Opus 4.7 with `thinking: {type: "adaptive", display: "summarized"}` and `output_config: {effort: "xhigh"}`.
- Prompt caching via `cache_control: {type: "ephemeral"}` on system + evidence object.
- Pipeline parallelism via `asyncio.gather` after VEP gates the rest.
- All 9 sources degrade gracefully — a missing source flags `confidence: missing` and Opus 4.7 explicitly notes it in CONFLICT RESOLUTION.
