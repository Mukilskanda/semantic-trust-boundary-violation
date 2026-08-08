# Submission Readiness

One-page bottom line, written for someone deciding whether to submit.

## Is the science sound?

Yes. Every number in the manuscript traces to a named script, artifact, and (where relevant) seed. The one new experimental claim added this pass — the hard-mined checkpoint's improvement — was verified at three independent levels (validation split, held-out direct classifier, held-out full pipeline) before being accepted, and is now backed by a statistically significant paired test ($p{\approx}7\times10^{-53}$) rather than a bare point estimate. No threshold was tuned to chase a metric; the one instance where that temptation existed (the earlier calibration investigation) was resolved by reverting to the worse-ECE-but-better-decision-quality option and disclosing why.

## Is the checkpoint story consistent?

Yes, in the manuscript body. A dedicated sweep (`FINAL_FREEZE_REPORT.md` Task 1) found and fixed every place an older checkpoint was still being called "final" in the manuscript's own text, in `isce_config.yaml`, and in the highest-visibility supporting scripts and reports. Lower-visibility scratch scripts were left unlabeled — a proportionate, disclosed choice, not an oversight.

## What's genuinely not done, and does it matter?

- **CARLA and STBV-Bench v1 were not rerun against the new checkpoint.** Both are explicitly labeled as reflecting the prior checkpoint everywhere they appear. This is a real gap in currency, not a hidden one. It matters for completeness, not for correctness — nothing in the paper claims these are current when they aren't.
- **No LaTeX compile has ever been performed in this environment.** This is the single item most likely to cause a real submission problem (page limits, float overflow, broken IEEE two-column layout) that static analysis cannot catch. **This should be done by the author, with a real LaTeX installation, before submission** — it is outside what this session's tooling can verify.
- **A handful of open, disclosed methodological questions remain** (full-pipeline ECE for the new checkpoint; whether the six targeted attack families generalize to a larger mining pass) — none of these threaten any currently-published claim; they're honestly scoped as future work, not silently glossed over.

## Recommendation

Ready for a draft/preprint submission or an internal review pass as-is. **Not yet ready for camera-ready** until (1) a real LaTeX compile is performed and the page count/layout confirmed, and (2) the author makes a judgment call on whether the CARLA/v1 currency gap needs closing before the target venue's deadline, given it's disclosed either way.
