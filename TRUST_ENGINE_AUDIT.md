# Trust Engine Audit

Traces where false positives on STBV-Bench v2.5b's full-pipeline evaluation first appear: B3 itself, or the Trust Decision Engine's fusion/policy logic on top of it.

## Method

For every benign v2.5b sample flagged Caution/Reject by the full pipeline (1,734 of 4,734), classified into two categories using the corrected per-sample data (`pipeline_pmalicious_CORRECTED.csv`):
- **B3-originated**: B3's own raw score already exceeds 0.5 (B3 itself would call this malicious even under a naive threshold).
- **Policy-originated**: B3's raw score is below 0.5 (B3 correctly leans benign), but the confidence-aware-benign floor (confidence $\geq 0.85$ required to accept a BENIGN call) escalates the decision anyway.

## Layer-by-layer decision propagation

1. **B1 (SCSV)**: no fatal findings on v2.5b's synthetic messages (all structurally valid, non-replayed, single-shot) — confirmed by inspecting the `b1` field of the full-pipeline run; B1 contributes zero false positives on this benchmark, consistent with its design (Section IV.A of the manuscript).
2. **MBD**: cold-start on every v2.5b sample (single message per synthetic vehicle, no history) — `evidence: ["No history yet; baseline assumed valid."]` on every sample checked. MBD contributes zero false positives on this benchmark for the same structural reason.
3. **B3**: the sole source of semantic risk signal. Of the 1,734 benign false positives, **1,031 (59.5%)** have B3's own raw ensembled score $\geq 0.5$ — B3 itself, even under a naive threshold, calls these malicious. This is Stage 1 of `PIPELINE_DIFFERENCE_REPORT.md` (the text-synthesis distribution shift) manifesting as a real B3 misclassification, not a fusion artifact.
4. **Trust Decision Engine (confidence-aware-benign floor)**: the remaining **703 (40.5%)** benign false positives have B3 correctly leaning benign (raw score $<0.5$) but are escalated anyway because BENIGN-side confidence falls under the deployed 0.85 floor. This is Stage 2 — a policy/calibration effect, not a B3 classification error per se.
5. **Dempster-Shafer / Yager fusion**: confirmed, by the same mechanism proved in the manuscript's Section V (Propositions 1–3), that fusion never *introduces* a false positive B3 and the floor logic did not already produce — fusion combines B1's clean mass (vacuous or near-full-trust on v2.5b, since B1/MBD report nothing) with B3's mass; when B3's mass alone is enough to cross a floor, fusion's pignistic score reflects that faithfully. No case was found where fusion's mass combination itself (as opposed to the floor rules layered on top of it) manufactured a Reject that neither B1 nor B3's floor-rule evaluation alone would have produced.

## Where each false positive "first appears"

| Origin | Count | % of FPs | Mechanism |
|---|---|---|---|
| B3's own raw score | 1,031 | 59.5% | Text-synthesis distribution shift (Stage 1) |
| Confidence-aware-benign floor | 703 | 40.5% | Ensembling/calibration mismatch (Stage 2) |
| Fusion mass combination itself | 0 | 0% | No case found where DS/Yager combination, independent of the floor rules, manufactured a new false positive |
| B1 or MBD | 0 | 0% | Neither layer has any content-reading capability; both report clean on this benchmark by construction |

## Conclusion

**Both real false-positive sources trace to B3 (its raw classification and its confidence calibration), never to the Dempster-Shafer/Yager fusion mechanism itself.** This is consistent with, and further evidence for, the manuscript's existing claim (Section on Theoretical Properties) that every measured failure in this paper traces to an upstream evidence-generating layer, never to fusion's own mathematics. The confidence-aware-benign floor is not a fusion defect — it is a deliberate, documented conservative-safety design choice (requiring high confidence to accept a benign verdict) whose *interaction* with an uncorrected calibration mismatch (Stage 2) amplifies an otherwise-smaller B3 classification gap (Stage 1) into a larger deployed-precision cost. Fixing the calibration mismatch (recommended next step, `PIPELINE_DIFFERENCE_REPORT.md`) would be expected to shrink, not eliminate, the Stage 2 contribution, since B3's own Stage 1 misclassifications (1,031 of 1,734 FPs) would remain regardless of calibration.
