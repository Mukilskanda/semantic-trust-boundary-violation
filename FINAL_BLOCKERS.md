# Final Blockers

This file lists **only** issues that cannot be resolved by further
writing, documentation, repository analysis, or figure/diagram design —
only by new research, a new dataset, or a new experiment. It is
deliberately narrower than the full Limitations section
(`DISCUSSION_AND_LIMITATIONS.md`, L1–L16) and narrower than
`FINAL_READINESS_REPORT.md`'s remaining-weaknesses list, both of which
also include items resolvable by manuscript or repository work alone.

Items that were open earlier in this project but are **not** listed here
because they were closed by documentation/analysis/design work, not new
research: the CP wiring bug (fixed, commit `6dc7df80c`), the manuscript
integration/assembly itself (`stbv_paper.tex`, this round), the four
architectural diagrams and `fig1.png`'s absence (asset/design gaps, see
below), and the parameter sensitivity sweep (closed with existing code
and logged data).

## 1. No external semantic-attack corpus exists to validate against

STBV-Bench v1/v2, the VeReMi kinematic companion bench, and the
mixed-threat bench are all internally constructed (real VeReMi
kinematics plus a seeded semantic transformation engine built for this
project). No independently-authored, external corpus of V2X semantic
attacks exists in the published literature to cross-validate B3's
generalization against attack phrasing this project's own transformation
engine did not generate. This is a field-level gap, not a repository
gap: closing it requires either commissioning/collecting such a corpus
(a new data-collection effort) or waiting for one to appear in the
literature. Corresponds to Limitation L12.

## 2. No adaptive-attacker / red-team evaluation

Every attack in every benchmark in this work is fixed and known in
advance to the transformation/injection engine that generates it. No
experiment measures B3 or the fused architecture against an attacker
that iteratively probes the deployed checkpoint and adapts its phrasing
or kinematics to evade detection (adversarial search, red-teaming, or a
genuine online adaptive-attack loop). This is the standard threat model
expected at security-focused Transactions venues (TDSC, TIFS) and is
explicitly out of scope for what existing repository code and logged
data can answer — it requires a new experimental campaign, not
re-analysis. Corresponds to Limitation L14.

## 3. Robustness testing covers text perturbation only, not a formal guarantee

The robustness evaluation (`b3_eval/results/robustness.json`) measures
label-flip and over-defense rates under eleven named text-perturbation
families, revealing a serious 100% over-defense rate for
instruction-hiding and role-confusion phrasing. This tells us the model
is measurably brittle to certain phrasings, but it is an empirical
probe, not a certified robustness bound — no experiment in this work
establishes a formal guarantee (e.g., verified robustness radius) against
an arbitrary perturbation within some threat model. Formal verification
of a fine-tuned transformer classifier's robustness is itself an open
research problem in the broader NLP-security literature and is well
beyond what this project's existing code or data can close by further
analysis.

## Not blockers — resolvable without new research (listed for contrast, not duplication)

- **`fig1.png`'s absence.** This is a missing-asset issue (the original
  manuscript referenced an image not present in this repository
  checkout), not a research gap — resolved by locating or redrawing the
  figure, not by an experiment. Tracked in `FIGURE_PLACEMENT.md` and
  `FINAL_CHANGELOG.md`, not repeated here.
- **The four unproduced architectural/workflow diagrams** (Vertical
  Architecture, STBV-Bench Generation Pipeline, Experimental Workflow,
  Threat-Class Coverage Matrix as a rendered figure). These are diagram
  design tasks — every fact each diagram would depict already exists in
  this manuscript's prose, tables, and appendices. Tracked in
  `FIGURE_PLACEMENT.md`, not repeated here.
- **Related Work depth.** `RELATED_WORK.md` reflects single-session
  targeted search, not a systematic literature review. This is closable
  by further literature search effort, which is available now, not
  contingent on new data or experiments.
- **CP's zero measurable contribution.** Traced to a specific,
  understood data-generation gap (`event_label` never populated for any
  benchmark generator) rather than an unknown or a research question.
  Closable by implementing event-label generation for at least one
  benchmark — an engineering task using code already in this repository,
  not new research. Tracked as Limitation L1.
