# Reproducibility and Parameter Appendix

Every value below is either read directly from a committed file/checkpoint
artifact (cited by path) or is stated as **not implemented as a literal
tunable constant** where that is the honest answer — per the mission's
non-negotiable rule against fabricating metrics or parameters.

## 1. Semantic classifier (B3)

| Property | Value | Source |
|---|---|---|
| Architecture | `DebertaV2ForSequenceClassification` (DeBERTa-v2 family) | `.../model/semantic_gate_v3/config.json` |
| Hidden size | 768 | same |
| Hidden layers | 6 | same |
| Attention heads | 12 | same |
| Intermediate size | 3072 | same |
| Max position embeddings | 512 | same |
| Vocabulary size | 128,100 | same |
| Relative attention | `p2c`, `c2p` (position-to-content, content-to-position) | same |
| Parameter count | **141,896,450** | `b3_eval/results/model_benchmark.json` (`INCUMBENT`) |
| Tokenizer | `DebertaV2Tokenizer`, SentencePiece (`spm.model`) | `.../tokenizer_config.json` |
| Max sequence length at inference | **256 tokens** | `pipeline/b3_bridge.py:223` |
| Labels | `BENIGN` (0), `MALICIOUS_SEMANTIC_MANIPULATION` (1) | `config.json` |
| Checkpoint file size | 567,622,450 bytes | verified this round |
| Checkpoint SHA-256 | `9ee7475e08f76ce6961c55204657a380d5ef1c2c9dac6a9d46543a7c42c2f5d2` | verified this round, matches `README.md` |

### Training hyperparameters (recovered from the checkpoint's own `training_args.bin`, not re-derived or estimated)

| Hyperparameter | Value |
|---|---|
| Learning rate | $2\times10^{-5}$ |
| Epochs | 15 |
| Per-device train/eval batch size | 16 / 16 |
| Optimizer | AdamW (`adamw_torch`) |
| LR scheduler | Linear, warmup ratio 0.1 |
| Weight decay | 0.01 |
| Precision | FP16 |
| Seed | 42 |
| Gradient accumulation | 1 |

**Honesty note:** this document reports these hyperparameters as *read
from the artifact that already exists in the repository*. It does not
reproduce the training run itself, and the original training dataset's
raw files (as opposed to derived scripts referencing it) are not present
in this checkout — this is stated as a limitation (see
`PUBLICATION_PROGRESS.md`, and the dataset-leakage discussion in
`HANDOFF_SUMMARY.md` §3/§10) rather than concealed. Inference hardware
used throughout this evaluation: NVIDIA GeForce RTX 4050 Laptop GPU
(6,141 MiB VRAM), CUDA 13.1, PyTorch 2.7.1+cu118, Transformers 5.12.1,
Python 3.13.0, Windows 11.

### Calibration
Post-hoc temperature scaling, single scalar parameter $T$, fitted on
$n=85$ labeled samples by minimizing negative log-likelihood (standard
Guo et al. 2017 procedure). Fitted value: $T=2.144598$ (`b3_eval/results/calibration.json`).
This is the only learned/fitted scalar parameter in the entire pipeline
outside of B3's own pretraining — every other threshold below is a fixed
design constant, not fitted from data.

## 2. Fusion and decision thresholds — what exists in code vs. what is idealized in Section II

**This is reported precisely because glossing over it would be a
reproducibility failure a rigorous reviewer would (correctly) catch.**
Section II's Eqs. (1)–(6) — $T_{MBD}=\sum w_i f_i$, $T_{CSIA}=\alpha T_{MBD}+(1-\alpha)C$,
$T_{Semantic}=\sum \beta_i S_i$ — are **architectural/conceptual
formalizations of what each layer's evidence represents, not literal
computations performed by named, tunable constants in the current
codebase.** Verified by direct code inspection (`grep` for `alpha`/`ALPHA`
across `mbd/*.py` and `b2_explain/*.py` returns no matches):

- **MBD** does not compute a single weighted sum $\sum w_i f_i$. It
  computes several independently-thresholded sub-scores (`kinematic_score`,
  `temporal_consistency`, `replay_score`, `sybil_score`, `collusion_score`,
  `anomaly_score`), each from rule-based checks against fixed physical
  bounds (e.g., `MAX_ACCEL`, `MAX_HEADING_RATE` in `mbd/mbd_layer.py`),
  not from a learned or hand-tuned linear combination.
- **CSIA/B2** does not compute $\alpha T_{MBD} + (1-\alpha)C$ with a named
  $\alpha$ constant anywhere in `b2_explain/`. It recombines B1 and MBD
  evidence into a `validation_score`/`confidence_calibration` pair,
  further folded with CP's own components inside `pipeline/orchestrator.py`
  (the CP evidence fold, spatial/speed/heading/diversity weighted
  0.35/0.25/0.20/0.20 — see below — is the one place in the codebase
  where a literal fixed weighted sum matching the paper's style of
  equation actually exists).
- **The Trust Decision Engine** does not compute $T_{Semantic}=\sum\beta_i S_i$
  with named $\beta_1$–$\beta_4$ constants. It converts B1(+MBD+CP)-derived
  evidence and B3's label+confidence into two independent Dempster-Shafer
  mass functions and combines them with Yager's rule (`trust_engine/dempster_shafer.py`,
  `trust_engine/decision_engine.py`), exactly as described in Section II-E —
  this part of Section II is an accurate description of the implementation.

**What this means for the manuscript**: Eqs. (1), (3), and (4) should be
presented explicitly as the *conceptual* formulation of what each layer's
evidence is meant to represent (useful for explaining the architecture's
design intent to a reader), while Eqs. (7)–(13) (Dempster-Shafer
representation, Yager fusion, pignistic transform) should be presented as
the *actual, implemented* fusion mechanism, since that correspondence is
verified in code. This distinction was not previously stated in the
manuscript and is corrected here.

### Fixed constants that do exist, verified in code, with rationale

| Constant | Value | Location | Origin |
|---|---|---|---|
| $\tau_H$ (crypto/fused-trust Accept threshold) | 0.70 | `trust_engine/policy.py:51` (`cryptographic_caution_below`) | Fixed design constant, **not tuned via search**; a round, interpretable value chosen by the architecture's designers. |
| $\tau_L$ (crypto/fused-trust Reject threshold) | 0.40 | `trust_engine/policy.py:50` (`cryptographic_reject_below`) | Same — fixed, not tuned. |
| B3 high-confidence risk band | 0.85 | `trust_engine/policy.py:42`, `pipeline/b3_bridge.py` (`B3RiskPolicy.high_confidence`) | Fixed design constant. |
| B3 medium-confidence risk band | 0.60 | `trust_engine/policy.py:43` | Fixed design constant. |
| Max source confidence (epistemic budget, prevents a dogmatic DS source) | 0.98 | `trust_engine/decision_engine.py:39` (`MAX_SOURCE_CONFIDENCE`) | Fixed; documented rationale in-code: prevents any single source from acquiring absolute veto power under Dempster's rule. |
| CP consistency weights (spatial / speed / heading / diversity) | 0.35 / 0.25 / 0.20 / 0.20 | `cp/cp_layer.py` | Fixed design constants (sum to 1.0); the one place in the codebase matching the paper's literal weighted-sum style. |
| B3 tokenizer max length | 256 | `pipeline/b3_bridge.py:223` | Fixed operational constant. |
| Semantic evidence floor rule | Medium/low confidence semantic risk floors decision at $\geq$ Caution; high confidence floors at Reject; semantic evidence never relaxes a crypto-derived Reject | `trust_engine/decision_engine.py` | Explicit, documented asymmetric policy layered on top of DS fusion (not a claimed property of Yager's rule itself — stated as such in-code). |

**None of these thresholds have been subjected to a systematic
sensitivity analysis (grid search, ablation over threshold values, or
similar) in this evaluation effort.** This is stated here as an honest
gap, per the task's explicit instruction, and is added to Limitations
(Section VII) as future work: a sweep of $\tau_H$, $\tau_L$, and the B3
risk bands against the STBV-Bench v1 fixed slice, reporting the resulting
precision/recall/F1 tradeoff curve, has not been performed.

## 3. STBV-Bench construction (dataset reproducibility)

| Property | Value | Source |
|---|---|---|
| Underlying kinematic source | VeReMi Extension, public dataset | `DATASET_INTEGRATION.md` |
| Source pool size (v1) | 221,125 real flat reports across `ConstPos_1416`, `DataReplay_1416_full`, `DoS_1416_full` | `DATASET_INTEGRATION.md` |
| v1 evaluation slice | $n=10{,}000$, drawn without replacement, seed = 7 | commit `33b572be4` message; **the build manifest itself is not committed** (`data/` is gitignored) — stated as Limitation L9 in `PUBLICATION_PROGRESS.md`, reproducible via `build_stbv_bench.py --seed 7` but not independently re-verified against a committed artifact this round |
| v1 corpus prevalence | 70.07% malicious / 29.93% benign | `VERIFICATION_ADDENDUM.md` §3, confirmed from `results/ablation/ablation_summary.json` config-1 confusion counts |
| Per-sample seed | `seed_master * 1_000_003 + i` (deterministic, unique per sample) | `stbv_bench/build_stbv_bench.py` |
| Attack families | 20 + `benign_control` | `stbv_bench/transformations.py` |
| Kinematic companion bench | $n=13{,}511$ real messages, 360 vehicles, seed=13 | `results/veremi_kinematic/manifest.json` |

## 4. Statistical methodology

| Method | Setting | Where used |
|---|---|---|
| Bootstrap CI | 2,000 resamples, percentile method (2.5/97.5), fixed seed=42 | `stbv_bench/analyze_ablation.py`; all F1 CIs reported in Table I/Table II |
| McNemar's test | Continuity-corrected ($|n_{01}-n_{10}|-1)^2 / (n_{01}+n_{10})$, chi-square(1) via `erfc` | `stbv_bench/analyze_ablation.py` |
| Cohen's $h$ | $h = 2\arcsin\sqrt{p_2} - 2\arcsin\sqrt{p_1}$ on paired binary positive rates | same |
| ECE / Brier | Standard binned reliability calibration error and Brier score, $n=85$ | `b3_eval/run_calibration.py` |
| ROC / PR (this round) | `sklearn.metrics.roc_curve`/`precision_recall_curve` on `score = 1 - trust\_score`, $n=10{,}000$ | `figures_v2/generate_figures.py` |

## 5. What remains open

- No systematic threshold/parameter sensitivity analysis (Section 2, above).
- STBV-Bench v1's 100k-sample build manifest is not independently
  re-verifiable from a committed artifact (Section 3, above).
- B3's original training data (raw files, as opposed to scripts that
  reference it) is not present in this checkout; training hyperparameters
  were recovered from the checkpoint's own metadata, not from re-running
  training.
