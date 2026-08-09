# Attack-Family Figure Audit

Reviewing the current `fig_attack_family_v25b` (per-family recall + false-negative counts, STBV-Bench v2.5b, Full STBV Framework) before regenerating anything.

## 1. What scientific question does this figure currently answer?

Nominally: "does detection quality vary across real semantic attack families?" Panel A (recall) and Panel B (FN count) both point at the same underlying fact -- which families have any missed attack.

## 2. Does the figure actually communicate useful information?

Panel B (false-negative counts) does -- it correctly identified that only 3 of 13 families have any FN at all. Panel A (recall, zoomed to 0.97-1.002) is the weak half: with real recall ranging only 0.990-1.000, the panel exists mainly to justify why Panel B is presented as counts rather than a rate, not to teach a new fact on its own.

## 3. Is the variation between attack families large enough to justify a recall chart?

No. Recall's coefficient of variation across the 13 families is **0.0027** (computed directly from `config_5.csv`: min 0.990, max 1.000, std 0.0027) -- by any reasonable standard this is a flat metric. Keeping it as a full chart panel overstates its informativeness.

## 4. Is the figure redundant with Table II / Table III?

Partially. Table III (`tab:v25b_pipeline`) already reports the aggregate recall (0.999) for the Full STBV configuration; a 13-bar recall panel that all cluster within 1 percentage point of that aggregate adds little beyond confirming the aggregate holds per-family too -- a fact statable in one sentence, not a full chart panel.

## 5. Would an IEEE reviewer learn anything new from this figure?

From Panel B (FN counts), yes -- a concrete, small, real cluster (`traffic_efficiency_lure`: 4/406) worth citing as a target for future work. From Panel A (recall), only marginally -- the reviewer learns recall doesn't collapse for any family, which is already stated in Table III's aggregate number.

## Conclusion: what to keep, what to replace

Keep the false-negative-count panel (real signal, not redundant). Replace the recall panel with a metric that is not near-constant across families -- selected via the systematic comparison in `ATTACK_METRIC_ANALYSIS.md`.
