# Publication Checklist

Quick-scan status for this pass's freeze. For detail, see `FINAL_FREEZE_REPORT.md`; for the underlying checkpoint work, see `HARDMINE_IMPROVEMENT_REPORT.md`; for the broader submission checklist (figures/bibliography/page-count, carried from earlier passes), see `READY_FOR_SUBMISSION.md`.

| Item | Status |
|---|---|
| Single final checkpoint referenced consistently | ✅ `semantic_gate_v3_mixed_lora_hardmine_merged`, SHA-256 `d126cc3...` |
| Prior checkpoints labeled, not silently mixed in | ✅ every reference relabeled "prior (Pass 1)" or given a supersession banner |
| Calibration temperature single-valued | ✅ $T{=}3.18$ in `isce_config.yaml`, matches manuscript |
| Deployment config single source of truth | ✅ `isce_config.yaml` verified to match manuscript's stated values |
| v2.5b tables/figures current-checkpoint | ✅ `tab:v25b`, `tab:v25b_ablation`, new `fig_v25b_hardmine` |
| STBV v1 explicitly labeled non-primary | ✅ already the case pre-pass (supplementary); figures now also caption-labeled prior-checkpoint |
| LaTeX mechanical integrity | ✅ 0 broken refs/labels/citations/figure files, re-verified after every edit |
| Statistical significance for the new checkpoint's improvement | ✅ McNemar $p{\approx}7\times10^{-53}$, added to manuscript this pass |
| Three-reviewer critique performed | ✅ `FINAL_MANUSAL_AUDIT.md`, 9 objections addressed or disclosed |
| CARLA rerun against new checkpoint | ❌ not possible — no live simulator instance in this environment |
| STBV v1 regenerated against new checkpoint | ❌ not done — deprioritized (supplementary benchmark), disclosed |
| LaTeX compiled with a real toolchain | ❌ not available in this environment (carried forward from prior passes) |
| Adaptive-attack table on current checkpoint | ❌ not rerun — labeled as prior-checkpoint throughout, unchanged this pass |
| b7/b9 bibliography entries independently verified | ❌ carried forward from prior passes, still open |

## Blocking vs. non-blocking

**Not blocking submission** (disclosed limitations, common in empirical systems papers): CARLA/v1 non-rerun, adaptive-attack checkpoint mismatch — all explicitly labeled in-text, not silently omitted.

**Blocking a camera-ready, not a draft submission**: LaTeX has never been compiled in this environment. Page count, float placement, and visual layout are unverified. This should be done with a real LaTeX installation before final camera-ready submission, independent of anything else in this report.
