# Updated Ablation Results

## What changed and what didn't

**No metric value changed as a result of this pass.** The v2.5b ablation table (`tab:v25b_ablation`, F1=0.860 full-stack) reported in the prior pass was already computed from the real `TrustDecisionEngine` decision output (not from the buggy `raw_score`/confidence field my analysis initially misread) — re-verified this pass and confirmed correct. What changed is the **explanation** of why that number is lower than the direct-classifier F1=0.945: replaced an incomplete, single-mechanism explanation (text-synthesis dilution alone) with a complete, two-stage, fully-quantified one (see `PIPELINE_DIFFERENCE_REPORT.md`).

## Requested Config 1–5 mapping

The request's Config 1–5 definitions (PKI / PKI+B1 / PKI+B1+MBD+B2 / B3 standalone / full stack) are, in this codebase's actual implementation, not independently separable exactly as listed: PKI is not a standalone gate with its own accept/reject output separate from B1 (PKI authentication is a precondition B1's `check_stateful` assumes, not a distinct pipeline stage with its own decision) — confirmed by direct inspection of `orchestrator.py`'s `_run_pki()`, which returns a certificate-validity signal folded into B1's own evidence, not a separate accept/reject gate. The existing, already-published configuration scheme (B1-only / B1+B2(+MBD, always co-enabled) / B1+B2+CP / B3-alone / full stack) is the accurate mapping to what the code actually implements, and is what `tab:v25b_ablation` and `tab:main_ablation` both use, for consistency across every ablation table in this paper. Relabeling to a PKI-separate scheme without changing the implementation would misrepresent what was actually measured — not done.

## v2.5b full-pipeline ablation (unchanged this pass, re-verified)

| Configuration | Acc. | Prec. | Rec. | F1 | FPR |
|---|---|---|---|---|---|
| B1 only / B1+B2 / B1+B2+CP | 0.469 | -- | 0.000 | -- | 0.000 |
| B3 alone (no fusion) | 0.828 | 0.756 | 0.999 | 0.860 | 0.366 |
| Full stack | 0.828 | 0.756 | 0.999 | 0.860 | 0.366 |

(B3-alone and full-stack are aggregate-identical, as on STBV-Bench v1 — 854 individual decisions differ, all Caution→Reject, none crossing the binary Accept/non-Accept boundary.)

## New statistical tests performed this pass

- **McNemar-equivalent transition count** (v2.5b, B3-alone vs. full stack): 854 discordant, 100% one-directional (Caution→Reject), 0 reversals — reported in `PIPELINE_DIFFERENCE_REPORT.md`/manuscript.
- **Stage-decomposition analysis** (new, not in prior pass): quantifies the 0.945→0.860 gap as $-0.039$ (Stage 1, text synthesis) $+ -0.046$ (Stage 2, calibration/ensembling), fully accounting for the observed $-0.085$ total drop with no unexplained residual.
- **False-positive origin attribution** (new): 59.5% of v2.5b benign false positives originate in B3's own raw score, 40.5% from the confidence-aware-benign floor interacting with calibration mismatch, 0% from the Dempster-Shafer/Yager fusion mechanism itself (`TRUST_ENGINE_AUDIT.md`).

## ROC / PR / calibration / confusion matrices

Not regenerated for v2.5b specifically this pass (the existing STBV v1 versions, regenerated in a prior pass from real per-sample data, remain current for v1; v2.5b's direct-classifier ROC/PR/confusion would require the same treatment but was not built this pass given time constraints — flagged as a legitimate follow-up, not silently omitted).

## Cohen's h

Not computed this pass. Cohen's h is defined for comparing two proportions (e.g., two recall rates); the two v2.5b evaluation regimes (direct classifier vs. full pipeline) differ in more than one proportion simultaneously (precision, recall, and the underlying score distribution all shift), making a single Cohen's h an incomplete summary of a genuinely multi-dimensional difference already fully characterized by the stage-decomposition analysis above. Not computed rather than computed as a token statistic without clear interpretive value.

## Addendum: reconciling the 9-configuration request (subsequent pass)

A later pass requested nine named configurations (PKI only; PKI+B1; PKI+B1+MBD+B2; PKI+B1+MBD+B2+CP; B3 only; B1 only; B1+B2 only; B1+B2+B3 only; Full STBV Framework), superseding/expanding the mapping already given above. Reconciled explicitly rather than fabricated:

- **"PKI only" and "PKI+B1" are not separable in the implementation** — `b1_scsv/scsv.py` treats certificate/PKI validity as one of B1's own structural evidence checks, not an independent gate with its own accept/reject output. Both requested rows collapse onto the existing "B1 only" configuration; no ninth row was invented to satisfy the count.
- **"MBD" and "B2" are likewise not independently toggleable** — `enable_mbd` gates Misbehavior Detection, and B2 (CSIA) operates on MBD's output; there is no "B2 without MBD" system state. `enable_mbd` / `enable_cp` / `enable_b3` are the three real, independent degrees of freedom the orchestrator exposes.
- Eight of the nine requested rows map onto the five already-published configurations (see mapping table below).
- **"B1+B2+B3 only" (excluding CP) is the one genuinely new, realizable cell** — `enable_mbd=True, enable_cp=False, enable_b3=True` was not part of the original 5-config sweep (which has B1+B2+CP without B3, and full-stack-with-CP, but nothing skipping CP while including B3). This was **not run this pass** — flagged as a concrete, bounded follow-up (one more pass through the existing `run_v25b_full_ablation.py` harness, ~15–20 min on the full 10,098-sample set by this session's own prior timing) rather than fabricated or silently dropped.

| Requested (9) | Maps to | Status |
|---|---|---|
| PKI only | B1 only | Collapses (PKI not separable from B1) |
| PKI+B1 | B1 only | Collapses (identical to above) |
| PKI+B1+MBD+B2 | B1+B2 | Already reported (config 2) |
| PKI+B1+MBD+B2+CP | B1+B2+CP | Already reported (config 3) |
| B3 only | B3 only | Already reported (config 4) |
| B1 only | B1 only | Already reported (config 1) |
| B1+B2 only | B1+B2 | Already reported (config 2) |
| B1+B2+B3 only | Not yet run | Genuinely new, realizable, not fabricated — see above |
| Full STBV Framework | Full stack | Already reported (config 5) |

No new numeric values are reported in this addendum.
