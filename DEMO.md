# 3-Minute Demo Script — HepVar

**Hackathon submission for "Built with Opus 4.7" (Cerebral Valley, April 21–26 2026).**

Format: **on-camera intro → screen-capture demo with voiceover → on-camera close.** Total ~3:00. Speak slightly slower than normal — gives the cards time to animate, and the personal opening lands harder. Audience is mostly Anthropic engineers; the spoken track avoids genetics jargon and lets the visuals carry technical flavor.

---

## [0:00 – 0:30] Human Hook — *on camera, neutral background*

> "Five years ago, my wife got sick. Her liver enzymes were high. She had chronic pain. Doctor after doctor tried to explain it, and the best answer was autoimmune hepatitis. She started immunosuppressive medication, with serious side effects, but something still did not fit. Years later, a fifth hepatologist suspected we might be dealing with a rare genetic liver disease, and ordered a genetic test. The test found a mutation in a gene that helps the liver work properly. But the report didn't say *this explains it.* It said: **Variant of Uncertain Significance.** That means: we found something in your DNA, but we do not know if it is causing disease. **For many families, that is the end of the road. For us, it became the beginning.**"

*Lower-third overlay: "Ariel Maia · Postdoc researcher, PhD, Molecular Biology · Porto Alegre, Brazil"*

---

## [0:30 – 0:50] Why It Matters — *B-roll: Brazil map / database visual / scattered papers. Voiceover.*

> "Thanks to my research background, and my wife's master's in genetics, we kept investigating. We searched databases, scientific papers, and ran computer simulations. We found enough evidence to support the right diagnosis — including a study where researchers had introduced her exact mutation into cultured cells and shown that it disrupts the protein's function. She changed medication. One month later, full recovery."
>
> "Most families do not have two molecular biology researchers at home. Most doctors do not have hours to chase scattered genetic evidence. **And most of the world's variant databases were built from European DNA — so for patients in Brazil, Latin America, and Africa, an uncertain answer is the default.** So I built HepVar."

---

## [0:50 – 1:20] The Workflow — *screen capture, paste variant, run*

> "HepVar is a clinical reasoning partner for uncertain genetic variants in rare liver disease. It does not diagnose. It helps doctors and patients understand what a finding might mean, what evidence supports it, what is missing, and what to check next."
>
> *(paste variant `chr7:87408188 T>C`, hit run)*
>
> "I'm entering my wife's actual mutation. Behind the scenes, HepVar does in twenty seconds what took us weeks by hand — pulling a dozen sources in parallel: population databases, clinical databases, protein-structure predictions from AlphaFold and AlphaMissense, regulatory predictions from AlphaGenome, and the medical literature in five languages."

---

## [1:20 – 1:55] Opus Synthesis — *synthesis pane streaming, click "show model reasoning" briefly*

> "Now Claude Opus 4.7 reads the assembled evidence. This is where Opus matters. It is not summarizing — it is reasoning through uncertainty. With extended thinking on, you can watch the deliberation: which clues are strong, which conflict, which are missing."
>
> *(point to literature card)*
>
> "Here, Opus surfaced a paper where researchers had introduced this exact mutation into cultured cells and shown that it breaks the protein's function. Direct experimental evidence the original lab report had not included. Opus found it, weighed it, and folded it into the verdict."
>
> "The verdict on my wife's mutation: **Pathogenic.** Auditable. A clinician is not forced to trust a black box."

---

## [1:55 – 2:25] What surprised me — *stay on ABCB4 screen throughout; voiceover for the aside, then click the audience toggle*

> "Two things surprised me. While testing other variants, Opus *unprompted* warned me about a specific common drug — given to a patient with one of those mutations, it can cause fatal liver failure. The model named the safe alternatives. I had not asked it to think about treatment."

*(click the audience toggle: technical → clinician → patient, let the same card visibly rephrase itself)*

> "Second — the same model serves three audiences without changing the data. The bioinformatician sees the scoring and the deltas. The clinician sees the action. The patient sees plain language, and the questions to ask their doctor next. One pipeline. Three reports. **Opus does the rephrasing — the science underneath does not change.**"

---

## [2:25 – 2:45] Evidence Gap & Chat — *scroll to evidence-gap section, then chat composer*

> "And HepVar does not stop at an answer. It says what to do next: which lab test would confirm the mechanism, what numerical result would strengthen the case. It turns a verdict into a roadmap. Because the entire evidence packet is prompt-cached, a doctor can ask follow-up questions for ten minutes without burning the institution's budget."

---

## [2:45 – 3:00] Closing — *back on camera*

> "A VUS should not mean *nothing can be done.* Sometimes it just means the evidence is scattered, underrepresented, or too hard to interpret alone. HepVar turns that uncertainty into a map: what we know, what we do not know, and what to investigate next. **I built it because this problem reached my family. I want it to help the next one, sooner.**"

---

## Recording checklist

- [ ] Cache is warm: all 14 source fixtures already exist at `evidence/fixtures/GRCh38_chr7_87408188_T_C/` — pipeline runs offline in `HEPVAR_DEMO_MODE=1` with zero network calls.
- [ ] Launch backend in demo mode:
      ```
      HEPVAR_DEMO_MODE=1 uvicorn api.main:app --port 8000
      ```
      Confirm `/health` returns `"demo_mode": true`.
- [ ] `ANTHROPIC_API_KEY` is loaded — Opus synthesis + audience-toggle translations still call live (which is what you want on screen).
- [ ] Tool output for ABCB4 displays **Pathogenic** verdict before recording starts. Wait for the final synthesis state.
- [ ] Browser at `http://localhost:3000`, zoom 110%, light mode.
- [ ] Backend logs visible in a hidden terminal in case of glitch.
- [ ] External mic if available; otherwise quiet room + earbuds-on-stand.
- [ ] Two takes minimum. Second take focuses on tightness — cut filler ("so", "basically", "you know").
- [ ] Lower-third overlay ready: "Ariel Maia · PhD, Molecular Biology · Porto Alegre, Brazil"
- [ ] Upload as **YouTube Unlisted** (more reliable scrubbing than Loom for judges).

## What to mention if asked

- ACMG/AMP per Richards 2015; Tavtigian Bayesian per Tavtigian 2020.
- Opus 4.7 with `thinking: {type: "adaptive", display: "summarized"}` and `output_config: {effort: "xhigh"}`.
- Prompt caching via `cache_control: {type: "ephemeral"}` on system + evidence object.
- Pipeline parallelism via `asyncio.gather` after VEP gates the rest.
- Twelve sources degrade gracefully — a missing source flags `confidence: missing` and Opus 4.7 explicitly notes it in CONFLICT RESOLUTION.
