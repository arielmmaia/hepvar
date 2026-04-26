# HepVar — Hackathon Submission Form

> Built with Opus 4.7 — Cerebral Valley Virtual Hackathon · April 21–26 2026
> Submission deadline: April 26th, 8:00 PM EST

---

## Team Name

HepVar

---

## Project Name

HepVar

---

## Selected Hackathon Problem Statement

**Build From What You Know**

---

## Project Description

Five years ago my wife was misdiagnosed with an autoimmune liver disease and put on lifelong immunosuppressants that didn't fully work. After four specialists and years of side effects, a fifth one finally suspected a rare genetic liver disease and ordered a genetic test. It found a mutation in a liver gene — but the lab couldn't tell us whether it caused her disease. Verdict: *"we don't know."*

That answer came back not because the mutation was harmless, but because she's Brazilian, and the world's genetics databases are built mostly from European DNA. My wife is a geneticist. I'm a molecular biologist. We spent weeks rebuilding the evidence by hand — including a study where researchers had introduced her exact mutation into cultured cells and shown that it disrupts the protein's function. She switched medications and was healthy in a month.

**HepVar is that workflow, automated.** It pulls a dozen genetic, structural, and literature sources in parallel and hands the package to Claude Opus 4.7 with extended thinking. Opus weighs conflicting evidence, names the specific next experiment that would resolve the uncertainty, and *unprompted* flags clinical safety issues — including, in one test, a drug contraindication that would have caused fatal liver failure. Three modes (technical / clinician / patient) re-frame the same report without changing a single number. Open source, MIT.

---

## Public GitHub Repository

`https://github.com/<your-handle>/hepvar`  *(TODO: push the repo public, MIT-licensed, before submitting. Verify `.env`, `my-academic-information/`, and any patient data are gitignored.)*

---

## Demo Video

`https://youtu.be/<unlisted-id>`  *(TODO: record from `DEMO.md`, upload as YouTube Unlisted.)*

---

## Thoughts and Feedback on Building with Opus 4.7

Five things surprised me while building HepVar.

**1. Extended thinking turns classification into an audit trail.** In medical genetics, a verdict without a defensible reasoning chain is unusable — clinicians won't act on a black-box label. With `thinking: {type: "adaptive", display: "summarized"}`, Opus 4.7 produces a deliberation a clinician can read line-by-line and challenge: stepping through each scoring criterion, noticing when one source conflicts with another, deciding which to trust and why. I never prompted for that transparency — it emerged from extended reasoning.

**2. The model tells you what to do next, unprompted.** I never asked Opus to recommend a specific experiment. With extended thinking on, it naturally asks itself *"what evidence would change this classification?"* and answers concretely — naming a specific lab assay and the numerical threshold that would resolve the uncertainty. That meta-cognition turns a report from a verdict into a roadmap.

**3. Unprompted clinical safety reasoning.** On a test mutation in a different liver-disease gene, Opus flagged a drug contraindication unprompted — patients with this mutation can die of liver failure if given a specific common medication. It named the safe alternatives. On a separate test, when the sequencing lab returned a mutation that was one DNA letter off from a famously pathogenic version, Opus noticed the discrepancy against its training, refused to silently proceed, and demanded a confirmatory test before any clinical decision. I prompted for neither behavior. Both emerged from depth of reasoning over the evidence.

**4. One pipeline, three voices.** HepVar exposes three audience modes — technical, clinician, patient. Same numbers, same evidence, different register. Opus does the rephrasing in one model with one prompt addendum per mode. The bioinformatician sees the scoring criteria and the deltas. The clinician sees the action. The patient sees plain language and the questions to ask their doctor next. The science underneath does not change. This is what makes the tool useful to people who would otherwise need a translator.

**5. Prompt caching makes interactive medicine economical.** The 3K-token instruction set + 10K-token evidence packet write the cache once; every conversational follow-up reads at one-tenth the cost. A clinician can interrogate a report for ten minutes without burning the institution's budget. This shifted my mental model — Opus is not a one-shot reasoner, it is a sustained thinking partner once the cache is warm.

---

## Did you use Claude Managed Agents? If so, how?

No. HepVar uses the Anthropic SDK directly with Opus 4.7's extended thinking and prompt caching, because a single variant → reasoned report is a synchronous workflow where the user wants to watch the model deliberate live, and where the entire evidence packet must remain in-context for follow-up chat.

Managed Agents would be a natural fit for the next iteration: **batch cohort re-classification.** A hospital hands HepVar a list of 500 historical Variant of Uncertain Significance calls and asks the agent to re-evaluate each one in the background, pulling fresh evidence from databases that have updated since the original curation date, and surfacing only the variants whose classification has moved. That is a long-running, hand-off-able workload Managed Agents are built for, in a way a single-patient interactive report is not.
