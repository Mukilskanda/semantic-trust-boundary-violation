# Verification Addendum to ABLATION_STUDY.md

Five additive checks requested on top of the committed n=10,000 layer
ablation, before treating its CP explanation as final. No previously
committed run is re-executed; everything below is either a new
computation over already-committed per-sample logs, or one small new
multi-message-window test (120 real fixture messages, not re-generated).

---

## 1. Cohen's h for the fusion-vs-no-fusion comparison

Already computed and saved in `results/ablation/ablation_summary.json`
(`divergence.config5_vs_config4.cohens_h`) but not stated as a number in
the prior write-up. Stating it explicitly:

**Config 5 (full stack) vs Config 4 (B3 without fusion): Cohen's h = -0.026.**

By Cohen's (1988) conventional bands (small ≈0.2, medium ≈0.5, large
≈0.8), **-0.026 is well below the "small" threshold** — a negligible
effect size on the binary positive-rate shift, even though the underlying
McNemar test is highly significant (p=3.06e-29) because n=10,000 gives
enormous power to detect even a tiny, consistent shift. Both facts are
true simultaneously and neither should be reported without the other:
the shift is real and systematic (not noise — see the 5-vs-4 flip table
in `ABLATION_STUDY.md` Step 4), but its magnitude on the binary
detection-rate scale is negligible. This is why Step 6's "small but real"
phrasing was chosen; "negligible effect size, statistically significant
count" is the precise version of that claim.

For reference, config 5 vs config 3 (B3 existing at all): Cohen's h =
**-1.096**, solidly in the "large" band — the two effect sizes differ by
roughly two orders of magnitude in Cohen's own units, which is the
correct way to see that "B3 existing" and "fusion on top of B3" are not
comparable-sized effects.

---

## 2. Three-way (ACCEPT/CAUTION/REJECT) outcome breakdown

New analysis (`scratch/analyze_3way_flips.py`, output committed at
`results/ablation/ablation_3way_analysis.json`) over the already-committed
`ablation_config_4.csv`/`ablation_config_5.csv`. Binary F1 (config 5 vs 4:
128 flips) only counts changes that cross the ACCEPT-vs-{CAUTION,REJECT}
boundary. Looking at the full three-way decision string reveals fusion is
doing more than that number suggests:

**Full-stack (config 5) decision distribution, all 10,000 samples:**

| Decision | n | % |
|---|---|---|
| ACCEPT | 5,972 | 59.72% |
| CAUTION | 1,944 | 19.44% |
| REJECT | 2,084 | 20.84% |

**Config 4 → Config 5 raw decision-string transitions:**

| Transition | n | % of all transitions |
|---|---|---|
| CAUTION → REJECT | 1,585 | 92.5% |
| ACCEPT → CAUTION | 128 | 7.5% |
| **Total transitions** | **1,713** | 100% |
| ACCEPT ↔ REJECT (hard flips) | **0** | **0.0%** |

This is a materially different picture from "128 flips": **fusion causes
1,713 real decision changes**, 1,585 of which (92.5%) are invisible to
binary F1 because both CAUTION and REJECT count as "positive" in that
metric. **Zero of the 1,713 transitions skip CAUTION entirely** — fusion
never converts an ACCEPT directly to a REJECT or vice versa in this
10,000-sample run. This is direct empirical support for the architecture's
stated design intent (`trust_engine/policy.py`'s own comments on the
floor rules): fusion is supposed to *route* uncertainty through CAUTION
rather than force premature binary calls, and on this evidence it
does exactly that, 100% of the time it changes anything at all.

**What the two transition types actually are, by attack family**
(from `ablation_3way_analysis.json`):
- **CAUTION→REJECT (1,585 samples, all genuine attacks)**: dominated by
  `priority_manipulation` (264), `context_inversion` (198),
  `role_manipulation` (179), `instruction_injection` (177),
  `temporal_context_drift` (163), `context_poisoning` (160),
  `hazard_amplification` (143), `infrastructure_semantic_manipulation`
  (120). These are real attacks where B3 alone only reached the
  CAUTION-equivalent MEDIUM/LOW risk band, but fusing in corroborating
  crypto/structural evidence escalates the call to REJECT — a genuine,
  correctly-directed escalation (recall gain), not noise.
- **ACCEPT→CAUTION (128 samples)**: 69/128 (54%) are `benign_control` —
  this is where config 5's precision loss vs. config 4 (1.0000 → 0.9829)
  actually comes from. The remaining 59/128 are real attacks (mostly
  `semantic_narrative_poisoning` 13, `mixed_semantic_attacks` 8,
  `multi_message_context_poisoning` 7, `indirect_prompt_injection` 6 —
  notably, these are drawn heavily from the "0% B3 recall" cluster
  identified in the original ablation) where fusion's crypto-side
  evidence catches something B3 missed entirely, converting an FN into a
  CAUTION (a partial recall recovery, not a full one — these still are
  not REJECTed).

**Revised statement for the manuscript** (replacing "fusion's marginal
contribution is small but real"): *fusion causes 1,713 real decision
changes on this 10,000-sample run, of which 0 are direct ACCEPT↔REJECT
reversals; 1,585 escalate an already-suspicious CAUTION call to REJECT
(recall-positive, on real attacks), and 128 add caution to a previously-
clean ACCEPT (54% of which are false positives on benign traffic, 46% of
which are otherwise-undetected real attacks). Binary F1 barely moves
(+0.0024) specifically because the CAUTION-mediated escalations are
invisible to a binary metric — a three-way metric is necessary to see
fusion's actual behavior, and this is worth stating as a methodological
point in the paper, not just a numeric footnote.*

---

## 3. Malicious:benign ratio and prevalence caveat

**STBV-Bench v1's corpus prevalence is 70.07% malicious / 29.93% benign**
(computed directly from config 1's confusion counts: 7,007 attacker
samples, 2,993 benign_control samples out of 10,000 — matches the build's
`--benign-fraction 0.30` parameter exactly, `data/stbv_bench/v1/manifest.json`).

**Caveat to attach wherever precision/FPR is reported for STBV-Bench
(added here for the manuscript, not previously stated):** these
precision/FPR figures are computed **at STBV-Bench's corpus prevalence
(≈70:30 malicious:benign)**, not at any claimed real-world/operational
attack prevalence, which is almost certainly far lower in deployment.
Precision in particular is highly sensitive to prevalence: the same
classifier's precision would be substantially lower on a corpus with
(e.g.) 1% real attack prevalence, even with identical recall/FPR. FPR
itself (a per-class rate) does not change with prevalence and remains the
more prevalence-robust number to cite for deployment-relevance claims;
precision/F1 numbers should always be paired with the prevalence they
were measured at, exactly as done here.

---

## 4. Empirical CP verification — and a real, previously-unknown bug found

**Method:** `scratch/verify_cp_empirical.py`, run against the existing
Phase 2 fixture scenarios (`scenarios/{sybil,replay,fabrication,collusion,
mixed,semantic}/`, 20 real multi-vehicle messages each, 120 total — not
regenerated, reused as-is). Unlike STBV-Bench's independent single
messages, these ARE genuine continuous multi-vehicle scenarios, so each
scenario was replayed statefully (growing message window, one persistent
pipeline per scenario per arm) through two arms: CP enabled vs. CP
disabled, otherwise identical. Output: `results/ablation/cp_empirical_verification.json`.

**Result: 0/120 decision flips between CP-on and CP-off, across all 6
scenario families, even though 114/120 steps had `num_reports > 1`**
(up to 20 real, distinct-vehicle reports in the window) and `cp_confidence`
was **exactly 1.0 on every single step** (the maximal/neutral value).

This directly answers the requested question: **it is a real bug, not a
benchmark artifact.** The original ablation's stated root cause ("CP only
contributes when a window has >1 message, and STBV-Bench only has
single-message windows") was **directionally correct but not the actual
mechanism**, and is superseded by this more precise, code-confirmed root
cause:

**Confirmed root cause:** `pipeline/orchestrator.py`'s `_run_cp` method
(constructing CP's input) never computes or passes an `event_label` to
`cp/cp_layer.py::cp_layer()`:
```python
# orchestrator.py, _run_cp (~line 266-288):
reports = []
weights = {}
for m in messages:
    flat = to_flat_report(m, origin)   # event_label is never extracted here
    ...
return cp_layer(reports, observation_weights=weights)   # event_label never passed
```
Compare `_run_mbd` (~line 226-230), which DOES compute and pass one:
```python
event_str = target_msg.get("event") or _extract_denm_event(target_msg)
flat = to_flat_report(target_msg, origin, event=event_str)
```
`cp_layer()`'s own logic (`cp/cp_layer.py:104`) is:
```python
observations_available = (event_label is not None) and not any(r.get("source") == "veremi" for r in reports)
```
Since `_run_cp` never supplies `event_label`, it is always `None`, so
`observations_available` is **always `False`**, which forces `cp_layer`
down its neutral/vacuous branch (`cp/cp_layer.py:133-139`:
`spatial_score = speed_score = heading_score = diversity_score =
confidence = 1.0`) **unconditionally, regardless of how many reports are
in the window or whether they actually agree or contradict.** This also
means `orchestrator.py`'s own CP evidence-fold gate,
`cp_has_shared_event = cp_dict.get("event_label") is not None` (line 607),
is unreachable-true by construction — it can never fire, because
`event_label` on the returned `cp_dict` is always the `None` that was
never overridden. This is fully consistent with, and now the confirmed
mechanism behind, the empirical zero-flips result above, and is
independent of window size: even a single-message window with a real
event field would hit the same `event_label=None` wall, because the bug
is in what `_run_cp` passes to `cp_layer`, not in how many messages are
in the window.

**This is a genuine implementation bug** (per the mission's own standard:
"Do NOT redesign or refactor the architecture unless you discover a
verified implementation bug" — this qualifies), **not fixed in this
session.** Per the explicit instruction not to alter or re-run the
existing ablation numbers this session, no code change is made here; the
fix is precisely scoped for a clearly separated follow-up: `_run_cp`
should derive an `event_str` the same way `_run_mbd` already does
(`target_msg.get("event") or _extract_denm_event(target_msg)`) and pass
it as `cp_layer(reports, event_label=event_str, observation_weights=weights)`.
That follow-up should be done as its own commit, with its own
before/after ablation re-run explicitly labeled as such (not blended into
this session's already-reported numbers), so the "don't artificially
improve existing numbers" instruction is honored precisely — the current
ablation results stand as accurately describing the code as it existed
when they were measured, with this bug now disclosed alongside them.

**Corrected framing:** CP's zero contribution in the original ablation
was previously attributed entirely to STBV-Bench's single-message-window
design. That framing understated the issue. The corrected framing is:
**CP's event-based contradiction/corroboration channel is currently
disconnected from ever activating, in any evaluation, regardless of
window size, due to a wiring bug in `_run_cp`.** STBV-Bench's
single-message design is a second, independent reason CP could not have
contributed even if the bug were fixed (num_reports would still be 1),
but it is not the primary or sole explanation, and the paper must not
claim it is.

---

## 5. Companion kinematic-attack result

STBV-Bench v1 is semantic-attacks-only by design (`DATASET_INTEGRATION.md`:
"VeReMi's own kinematic attack labels are NEVER relabelled as STBV
attacks"). B1/MBD/CP showing near-zero recall on STBV-Bench therefore says
nothing about whether those layers work — only that there was nothing in
THIS benchmark for them to catch. The companion result (MBD/B2/CP
evaluated against real VeReMi kinematic ground truth, on their own
benchmark) is required before the "complementary threat-class coverage"
framing can be used in the manuscript. This is being produced now as
Task 2 of the current work item (`results/veremi_kinematic/`); see
`PUBLICATION_PROGRESS.md` for the completed numbers once that run
finishes, and do not cite the "complementary coverage" framing in the
manuscript without it.
