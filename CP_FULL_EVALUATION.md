# CP Full Evaluation: Does a Realistic Event-Labeled Benchmark Let Cooperative Perception Contribute?

Every prior result in this paper reports that Cooperative Perception
(CP) contributes **zero** measurable effect on any evaluated benchmark
(`PUBLICATION_PROGRESS.md` L1; `CP_VALIDATION.md`, Appendix
`app:cp`), traced to a specific, understood cause: STBV-Bench's message
generator never populates the `event` field CP's consistency gate
requires, so `observations_available` is always `False` and CP returns
neutral/vacuous values regardless of window size.

This report does **not** attempt to artificially inflate CP's
contribution. Instead, it asks a narrower, honest question: **if CP is
given the kind of data it was actually designed for** (multiple vehicles,
a shared claimed event, real spatial/kinematic corroboration or
contradiction) **— constructed without changing CP's algorithm, the
Trust Decision Engine, or the evaluation methodology in any way — does
CP then contribute something measurable, and if so, what, exactly?**
The answer is **yes, CP contributes a real, mechanistically-understood,
double-sided effect** — a genuine attacker-detection improvement, at a
genuine false-positive cost, both precisely quantified below. Neither
side of that finding is hidden or averaged away.

**No code was modified to produce this evaluation.** CP (`cp/cp_layer.py`),
the orchestrator's evidence fold (`pipeline/orchestrator.py`), and the
Trust Decision Engine are used exactly as they exist elsewhere in this
paper. Only new benchmark **data** was constructed, and the pre-existing
`enable_cp` ablation flag (already used throughout this paper's other
ablation tables) was toggled.

---

## 1. Why STBV-Bench cannot answer this question, and what can

STBV-Bench's synthesizer produces free-text scene descriptions for a
single message at a time; it was never designed to emit a shared,
structured `event` claim across multiple vehicles' messages in the same
window, which is what `cp_layer.py`'s `event_label` parameter and
`observations_available` gate require (`cp/cp_layer.py`, line 96:
`observations_available = (event_label is not None) and not any(r.get("source")=="veremi" ...)`).
This is a data-generation gap, not an algorithmic one — confirmed
previously by replaying the one pre-existing fixture set that does
carry real event labels (`scenarios/collusion/`, 3 of 20 messages;
`CP_VALIDATION.md`), where CP's consistency scoring was shown to compute
correctly and non-trivially the moment real event-labeled data exists.

This report scales that same idea up into a deliberately designed,
realistic, 24-scene, 142-message benchmark (`cp_full_eval/`), covering
five distinct CP mechanisms, not just "more of the same fixture":

| Category | Scenes | Messages | What it tests |
|---|---|---|---|
| A. Genuine multi-vehicle corroboration | 5 | 30 | Does CP avoid false positives when honest vehicles genuinely agree on a real event? |
| B. Lone fabricator vs. honest majority | 6 | 36 | Does CP's contradiction channel catch a single attacker inconsistent with an honest majority — something B1/MBD (one message at a time) structurally cannot? |
| C. Colluding minority, consistent fabrication | 5 | 40 | The literature-documented weakness (Zhang et al., data-fabrication attacks, cited in this paper's Related Work): can 3 coordinated attackers, who agree tightly with each other, partially defeat pure statistical consistency fusion against a 5-vehicle honest majority? |
| D. Sparse reporting | 4 | 12 | Does low corroboration (2 senders only) correctly route to uncertainty, not false disbelief? |
| E. Natural sensor noise, no attacker | 4 | 24 | Does CP's fixed spatial-spread formula wrongly penalize honest variance from different vantage points on one real, large/ambiguous event? |

Every message uses the same nested ETSI-CAM-shaped schema as the
pre-existing, already-verified `scenarios/*.json` fixtures — no new
message format, no architecture change (`cp_full_eval/build_scenarios.py`).
Positions/speeds/headings are seeded (master seed `20260803`) and fully
reproducible.

## 2. Method

Each of the 24 scenes is replayed **statefully** — the message window
accumulates one message at a time, exactly the methodology
`stbv_bench/verify_cp_empirical.py` already used for the pre-existing
120-scenario CP check — through **four** pipeline configurations:

1. CP off, B3 off (diagnostic isolation baseline)
2. CP on, B3 off (diagnostic isolation — CP's own, unmixed contribution)
3. CP off, B3 on (realistic full stack, without CP)
4. CP on, B3 on (realistic full stack, with CP)

Both the diagnostic-isolation and full-stack arms are reported because
they answer different, both-valid questions (matching this paper's
standing rule to never blend different-question results into one
number); this section reports the full-stack arm (3 vs. 4) since it
reflects the actually-deployed decision path, with the diagnostic arm
given in `cp_full_eval/results/cp_full_eval_analysis.json` for anyone
who wants CP's effect with B3's own contribution held out entirely.

## 3. An honest confound, disclosed before the results: baseline false-positive rate is dominated by MBD, not CP

**Before reporting CP's effect, one fact must be stated plainly: this
benchmark's absolute false-positive rate, even with CP off, is high
(99/142, ≈70%) — and this is not a CP effect at all.** Direct inspection
of MBD's own sub-scores confirms the cause: MBD's `collusion_score`
climbs steadily as more vehicles report similar kinematics near the same
location within a short time window (observed directly: 0.0 → 0.25 →
0.50 → 0.75 across four accumulating benign reports in one example
scene, `cp_full_eval/results/cp_full_eval_results.json`). **The very
thing that makes data realistic for CP — multiple vehicles agreeing on
one shared event — is, from MBD's collusion heuristic's point of view,
kinematically indistinguishable from a Sybil/collusion attack signature.**
This is a genuine, honestly-disclosed tension in constructing a realistic
multi-vehicle corroboration benchmark, not a bug introduced by this
evaluation, and not evidence against MBD (which is doing exactly what it
is designed to do on data it was never built to see — MBD's other
benchmarks, VeReMi-derived and STBV-Bench, never present a tight,
same-timeframe multi-vehicle cluster this way).

**Consequence for how to read this report: the absolute false-positive/
decision counts below are confounded by MBD and must not be compared to
STBV-Bench v1/v2's FPR.** The only sound reading is CP's **marginal,
CP-attributable delta** — the difference between the CP-off and CP-on
columns on identical data — which isolates CP's own contribution from
this MBD confound by construction (both columns share the same MBD
behavior; only `enable_cp` differs).

## 4. Results: CP's marginal, attributable effect (full stack, $n=142$)

| Metric | CP off | CP on | Δ (CP-attributable) |
|---|---|---|---|
| Decision changes (any ACCEPT/CAUTION/REJECT change) | — | — | **33 / 142 steps (23.2%)** |
| Escalations toward CAUTION/REJECT | — | — | 33 (100% of changes) |
| De-escalations toward ACCEPT | — | — | 0 |
| `attack_detected` flag changes (CAUTION/ACCEPT → REJECT) | — | — | **11 / 142 steps** |
| Mean trust-score delta | — | — | −0.0049 |
| False positives (benign messages at CAUTION/REJECT) | 99 | 121 | **+22** |
| False negatives (attacker messages at ACCEPT) | 0 | 0 | 0 |

**Every single decision change is an escalation; zero are
de-escalations.** CP, in this design, only ever makes the architecture
more cautious, never less — a directionally conservative effect
consistent with the architecture's stated design principle that semantic/
corroboration evidence should only add caution, never relax a decision
(Section~II, this paper).

### 4.1 The real, attacker-specific benefit: lone-fabricator detection

Of the 21 attacker messages in this benchmark, only **6/21 (28.6%)**
reached `REJECT` (`attack_detected=True`) with CP off — B1, MBD, and B3
alone. **With CP on, 17/21 (81.0%) reach REJECT — CP newly catches 11
attacker messages that the rest of the stack missed entirely**, and does
so specifically and correctly: in 5 of the 6 `lone_fabricator_vs_honest_majority`
scenes, the single attacker's message is escalated from `CAUTION` (or
better, undetected) to `REJECT` **only** once CP is enabled, driven
directly by a measurable drop in CP's spatial/speed/heading consistency
score caused by that one inconsistent report (example:
`scene_005_lone_fabricator_vs_honest_majority`, attacker message: CP-off
decision `CAUTION`/`attack_detected=False` → CP-on decision
`REJECT`/`attack_detected=True`). **This is a real, non-fabricated,
attacker-specific detection improvement that STBV-Bench structurally
cannot produce, because it never gives CP more than one report to
compare.**

### 4.2 The honest, literature-consistent partial weakness: coordinated collusion

The `colluding_minority_consistent_fabrication` category (3 attackers,
tightly self-consistent, contradicting a 5-vehicle honest majority) was
designed specifically to test the documented weakness that coordinated
fabrication can partially defeat pure statistical consistency fusion
(Zhang et al., cited in Related Work). The precise, message-by-message
result (`cp_full_eval/results/cp_full_eval_results.json`) is genuinely
mixed, and is reported exactly as measured, not rounded toward either a
clean success or a clean failure:

- **The first colluding attacker's message is, in effect, never caught
  by CP: it evades detection (`attack_detected` stays `False`) in 4 of
  the 5 scenes**, even after the full window (all 8 messages) has
  accumulated. Only 1 of 5 scenes catches the first colluder immediately.
  This is a real, direct confirmation of the literature-documented
  weakness — three tightly self-consistent colluders are, at this
  window depth, largely indistinguishable from a genuine small cluster
  of honest vehicles by pure spatial/speed/heading statistics alone.
- **CP's marginal contribution concentrates at the second colluding
  message**: in 4 of the 5 scenes, the second colluder's message is
  newly escalated to `REJECT` specifically because CP is enabled
  (`attack_detected` `False`→`True`, CP off vs. on); the fifth scene had
  already reached `REJECT` on this message without CP.
- **By the third colluding message, the rest of the stack (B1+MBD+B3)
  has usually already caught up on its own**: 4 of 5 scenes reach
  `REJECT` even with CP off by this point, so CP's additional,
  attributable contribution at the third message is smaller — one
  further scene.

**Read together: collusion specifically and substantially defeats CP's
first-message detection (4/5 scenes), CP's real value in this category
concentrates at the second colluding report once the deviation from the
honest majority has compounded, and the architecture's other layers
increasingly close the gap on their own as the window grows further.**
This is not rounded up to "CP defeats collusion" nor down to "CP fails
against collusion" — both would misstate what the per-message data
actually shows.

### 4.3 The real cost: a cold-start false-positive artifact, not a semantic signal

**22 of the 24 scenes** — including all three categories with **zero**
attackers present (`genuine_multi_vehicle_corroboration`,
`sparse_reporting_uncertainty`, `natural_sensor_noise_no_attacker`) —
show one spurious `ACCEPT`→`CAUTION` escalation each, always at the exact
message where the accumulating window first reaches **2** reports.
Direct inspection of CP's own diversity score at that step
(`cp_diversity≈0.289`, `cp_full_eval/figures/cp_fig_cold_start_mechanism.pdf`)
confirms the mechanism: CP's corroboration-deficit-to-uncertainty pathway
(`pipeline/orchestrator.py`'s CP evidence fold, "corroboration deficit"
branch) reduces confidence whenever few unique senders have been seen so
far, **regardless of whether those senders agree or disagree** — this is
by design a measure of evidence *quantity*, not evidence *quality*, and
early in any window, quantity is inherently low no matter how honest the
traffic is. By the third accumulated report, diversity climbs
(`≈0.489`+) and the effect disappears. **This is a real, CP-attributable
cost (22 spurious `CAUTION` escalations, all at `CAUTION` severity, never
`REJECT`), not an argument that CP is broken — it is a specific,
mechanistically-identified, narrow artifact of evaluating corroboration
in windows that are still very short**, and it is reported here because
it is the honest other half of enabling CP on real multi-vehicle data,
not because it was sought out.

## 5. Per-category summary (full stack)

| Category | Decision changes | `attack_detected` changes | Attacker msgs newly caught | Benign msgs spuriously escalated |
|---|---|---|---|---|
| A. Genuine corroboration (no attacker) | 5/30 | 0 | — | 5 |
| B. Lone fabricator vs. majority | 10/36 | 5 | 5/6 | 5 |
| C. Colluding minority | 11/40 | 6 | 6/15 total (1st colluder: 1/5 scenes; 2nd colluder: 4/5 scenes newly caught by CP; 3rd colluder: 1/5 scene) | 5 |
| D. Sparse reporting (no attacker) | 3/12 | 0 | — | 3 |
| E. Natural sensor noise (no attacker) | 4/24 | 0 | — | 4 |

Figures: `cp_full_eval/figures/cp_fig_attacker_detection.pdf` (6/21 →
17/21 attacker-detection recovery), `cp_fig_decision_changes_by_category.pdf`,
`cp_fig_net_effect.pdf` (11 true-positive recoveries vs. 22 spurious
escalations), `cp_fig_cold_start_mechanism.pdf` (diversity score vs.
window position).

## 6. What this does and does not establish

**Established:** CP's algorithm, when finally given data shaped the way
it was designed to consume, contributes a real, measurable,
mechanistically-traceable effect — both a genuine attacker-detection
improvement (11 net new catches) and a genuine, narrow false-positive
cost (22 cold-start escalations, all capped at `CAUTION` severity). CP's
zero-contribution finding on STBV-Bench (`app:cp`, L1) is confirmed to be
a data-generation artifact specific to STBV-Bench, not evidence that
CP's algorithm has nothing to contribute in principle.

**Not established:** this does **not** mean CP is ready to be folded
into STBV-Bench's headline numbers, or that this benchmark's absolute
false-positive rate is representative of real deployment — §3's MBD
confound means this benchmark's own FPR is not comparable to STBV-Bench
v1/v2's, and this benchmark ($n=142$) is far smaller and deliberately
scenario-stratified rather than randomly sampled at scale. This report
answers "can CP contribute, mechanistically, on the right data" — it
does not re-run STBV-Bench with CP newly working, which would require
extending STBV-Bench's own generator to emit shared event labels across
multi-vehicle windows, an unscoped, not-attempted engineering task
distinct from this evaluation.

## 7. Recommendations

1. **Do not claim CP "works" or "doesn't work" as a single verdict.**
   Report both halves together: real attacker-specific detection gains,
   and a real, narrow, mechanistically-understood false-positive cost
   concentrated at short window depths.
2. **The cold-start artifact (§4.3) is fixable without touching CP's
   algorithm**: gating the corroboration-deficit-to-uncertainty pathway
   behind a minimum window-depth (e.g., do not apply it until $\ge 3$
   reports have accumulated) would plausibly remove most of the 22
   spurious escalations while leaving the genuine contradiction-channel
   detections (§4.1, §4.2) untouched — proposed as a concrete, scoped fix
   for future work, not attempted here since the task was to evaluate CP
   as-is, not modify it.
3. **Extending STBV-Bench's own generator to emit shared event labels
   across multi-vehicle windows** (closing L1 for the paper's actual
   headline benchmark, not just this supplementary evaluation) remains
   the correct long-term fix, and this report's scenario-construction
   method (`cp_full_eval/build_scenarios.py`) is a directly reusable
   template for doing so.
4. **The MBD/CP confound (§3) should itself be named as a limitation**
   of constructing realistic cooperative-perception benchmarks generally,
   not just of this one: any benchmark that gives CP genuine multi-
   vehicle agreement to fuse will, by the same token, resemble MBD's
   collusion-detection surface signature, and future benchmark design in
   this space should account for that overlap explicitly rather than
   being surprised by it.

## Evidence index

- `cp_full_eval/build_scenarios.py` — scenario generator, 5 categories, seeded
- `cp_full_eval/scenarios/scenes.json`, `manifest.json` — the 24-scene, 142-message corpus
- `cp_full_eval/run_cp_full_eval.py` — stateful replay through 4 pipeline configurations; no code/architecture changes, only `enable_cp`/`enable_b3` flags (pre-existing switches)
- `cp_full_eval/results/cp_full_eval_results.json` — full per-scene, per-step, per-config trace
- `cp_full_eval/analyze_cp_full_eval.py`, `cp_full_eval/results/cp_full_eval_analysis.json` — all metrics in this report
- `cp_full_eval/generate_cp_full_eval_figures.py`, `cp_full_eval/figures/*.pdf` — 4 figures
- `CP_VALIDATION.md`, Appendix `app:cp` — the pre-existing, smaller (3-message) CP verification this report extends
- `PUBLICATION_PROGRESS.md` L1 — the original zero-contribution finding on STBV-Bench, unchanged and still accurate for that benchmark
