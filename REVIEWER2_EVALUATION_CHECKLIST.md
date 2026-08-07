# REVIEWER2_EVALUATION_CHECKLIST.md — "does this convince me the model generalizes?"

Task 8's fresh adversarial pass, specifically scoped to the generalization
question, run against the paper post-hard-OOD-integration.

## Round 1

**Question:** does the new hard-OOD benchmark actually convince a skeptical
reviewer that B3 generalizes?

**Initial answer: not fully — one clear gap.** The corpus and result are
real and damaging-to-the-headline-number (exactly what was asked for), but
as first written, the F1=0.446 point estimate had no confidence interval,
so a reviewer could reasonably ask "is this gap real, or noise from a
288-message corpus?" — the same objection this paper already anticipates
and closes for its other headline numbers (STBV-Bench v1's baseline CI,
the CARLA bootstrap CIs).

**Action taken (standard, not exotic, per Task 8's instruction):** computed
a 2,000-resample percentile bootstrap CI (seed 42, same protocol as every
other bootstrap in this paper) for F1 and recall. Result: F1 0.446 [0.368,
0.520], recall 0.302 [0.238, 0.369] — confirms the gap is real, not a
sampling artifact (even the CI's upper bound sits below every other
benchmark's point estimate except STBV-Bench v2's, which measures a
different axis of difficulty). Integrated into `tab:hardood`, the Results
prose, and `HARD_OOD_RESULTS.md`.

## Round 2

**Question, re-asked after the fix:** with the CI in place, is there still
a legitimate "this doesn't prove generalization" objection?

**Answer: yes, one, and it cannot be closed within this task's constraints
(disclosed, not hidden).** The hard-OOD corpus, while genuinely
stylistically diverse and leakage-free, is a single, 288-message,
one-time-generated corpus from one local LLM (Mistral 7B) via one
prompting strategy. A maximally skeptical reviewer could argue this
demonstrates a gap *on this specific corpus's four styles*, not a fully
general claim about "colloquial/abbreviated real-world V2X phrasing" as a
category — a second, independently-constructed hard-OOD corpus (different
LLM, different style choices, ideally real human-authored radio-traffic
transcripts if any exist) would strengthen the claim further. **This was
not built**, because: (a) it would require either a second LLM (not
available in this environment beyond Mistral) or genuine human-authored
V2X radio-traffic samples (no such public dataset was identified, matching
the paper's own existing literature-search finding in
Appendix~\ref{app:external}); (b) the marginal evidentiary value of a
second synthetic corpus from the same LLM would be limited by the same
underlying dependency (one model's notion of "colloquial phrasing"); (c)
this is explicitly the kind of "exotic" over-extension Task 8 warns
against chasing indefinitely. The manuscript's own Limitations section
already states the honest, narrower claim this evidence *does* support
("B3 generalizes meaningfully within a grammatical, report-style register
and does not yet generalize to colloquial/abbreviated/idiomatic phrasing")
rather than the broader, not-yet-earned claim ("B3 does/doesn't generalize,
full stop").

## Final verdict

**Convincing, with the claim correctly scoped.** After the Round 1 fix,
the manuscript no longer overclaims in either direction: it does not treat
STBV-Bench's F1=0.995 as evidence of general capability (the hard-OOD
result now directly refutes that reading, with a real CI behind it), and it
does not treat the hard-OOD F1=0.446 as evidence the model doesn't work at
all (precision stays 1.000 wherever it fires, and the external corpus's
0.920 F1 on independently-authored grammatical text remains a genuine
positive result). The remaining generalization question this task chain
cannot fully close — whether the specific gap generalizes beyond one LLM's
notion of "colloquial phrasing" — is stated as an explicit open item in
this document and in `FINAL_EVALUATION_REPORT.md`, not silently accepted as
settled or hidden from the manuscript's own Limitations section.
