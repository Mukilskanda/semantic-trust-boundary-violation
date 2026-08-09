# Attack Visualization Redesign (Second Pass)

Supersedes the category-level bar+error-bar version of `fig_attack_family_v25b` from the immediately preceding pass, per this task's judgment that it "has become visually cleaner, but still communicates very little" -- accepted as correct: bar+error-bar collapses each category to two numbers (mean, std.\ dev.), which is still a summary, not the full real distribution.

## Step 1: every candidate metric, variance recomputed at the category level

| Metric | Values across 4 categories | Spread | Verdict |
|---|---|---|---|
| Recall | 0.997-1.000 | Negligible | Reject (confirmed a third time) |
| Precision, per-category FPR, per-category F1 | Not computable (v2.5b has no benign sub-families) | -- | Reject -- not available, not fabricated |
| Mean confidence | 0.959-0.988 | Small (range 0.029) | Reject alone -- too coarse on its own |
| Confidence std.\ dev. | 0.0008-0.099 | Large (2 orders of magnitude) | Real signal, but a single number still hides distribution shape |
| **Mean prediction entropy** $-p\log_2 p - (1{-}p)\log_2(1{-}p)$ | 0.096-0.176 | $\sim$1.8$\times$ | New this pass -- real, modestly informative |
| **Fraction of messages below $\tau_H{=}0.70$** | 0.0%-2.9% | Real, operationally meaningful (these are exactly the messages the Trust Decision Engine cannot confidently Reject on B3 evidence alone) | New this pass -- most directly tied to the architecture's own decision policy |
| Average trust score, calibration error | Redundant with confidence (the Trust Decision Engine's pignistic score for attacker rows on this benchmark is a monotone function of B3's confidence once B1/MBD/CP are structurally zero, established in the prior pass) | -- | Not built as a separate metric |

**Conclusion carried forward from the prior pass, strengthened**: no single summary statistic captures category difficulty well on its own. The real information is in the \emph{shape} of each category's confidence distribution -- how many messages sit near-ceiling vs.\ how many sit in the ambiguous zone below $\tau_H$ -- not any one number extracted from it.

## Step 2: family vs.\ category, re-confirmed

13 real families remain too fine-grained (most families have $n<450$ and produce visually indistinguishable near-1.0 clusters, per the two prior passes); the same 4 categories already defined in Section III (Threat Model) remain the right aggregation level -- large enough $n$ per group ($n{=}817$ to $1{,}706$) for a distribution plot to be meaningful, small enough count (4) to read at a glance.

## Step 3-4: candidates generated and scored

| Candidate | Sci.\ value | Readability | Novelty | Info.\ density | Reviewer usefulness | Verdict |
|---|---|---|---|---|---|---|
| Grouped category bars (mean confidence only) | 2 | 5 | 1 | 2 | 2 | Rejected -- this is the version being replaced |
| Bar + error bar (mean $\pm$ std, prior pass's design) | 3 | 4 | 2 | 3 | 3 | Rejected -- superseded; std.\ dev.\ alone still discards distribution shape (skew, outlier count) |
| Heatmap (category x metric) | 2 | 3 | 1 | 2 | 2 | Rejected -- too few cells (4x2-3) to justify a heatmap's overhead |
| Bubble plot (confidence x entropy, size = $n$) | 3 | 3 | 3 | 3 | 3 | Rejected -- encodes 3 real quantities but less precisely than a direct distribution plot; bubble-size comparison is imprecise |
| Entropy comparison alone | 2 | 4 | 2 | 2 | 2 | Rejected -- entropy spread (1.8$\times$) is real but the weakest of the three distribution-revealing options |
| **Boxplot / strip-plot of confidence distribution per category (selected)** | **5** | **4** | **4** | **5** | **5** | **Selected** |
| Violin plot | 4 | 3 | 4 | 5 | 4 | Close second -- rejected only because with $n$ up to 1,706 per category and a distribution this skewed (median $\approx$0.987, long lower tail), a violin's kernel-density estimate would visually smooth over the exact operationally-relevant threshold-crossing points a boxplot's whiskers and outlier dots preserve exactly |

## Step 5: why the boxplot wins, and why it answers "why," not just "which"

A boxplot of real per-message confidence, one box per category, with individual points below $\tau_H$ plotted as visible outlier markers, shows in one glance what two prior figure versions needed two panels and four summary numbers to approximate: every category's median sits at essentially the same high confidence ($\approx$0.987), so the boxes themselves look similar at first glance (correctly reflecting that recall is genuinely near-ceiling everywhere) -- but the \emph{whisker length and outlier count} differ sharply. Multi-Source Manipulation has zero outliers below $\tau_H$ (a tight box, no whisker extension) while Narrative Manipulation and Indirection show visible individual points scattered down toward 0.1-0.3 confidence -- the literal messages the architecture's floor rules route to Caution rather than a confident Reject. This is the figure directly showing \emph{why} these two categories are harder: not that the model is uncertain on average (medians are nearly identical), but that a real, visible minority of their messages are genuinely ambiguous to the classifier, while the other two categories have none.

## Updated Results discussion (Step 5 of the task)

The manuscript text accompanying this figure was rewritten to state the mechanism, not just the numbers: Narrative Manipulation and Indirection attack by reframing or displacing intent across a sentence (a diffuse signal), while Authority Claims and Multi-Source Manipulation attack via one concentrated, checkable assertion (a claimed authority, a fabricated cross-source agreement) -- a concentrated false claim is easier for a semantic classifier to key on than a diffuse reframing, which is exactly the pattern the boxplot's outlier points visualize.

## Confirmation

Every point plotted is a real per-message B3 confidence score from `config_5.csv`; the boxplot's quartiles, whiskers, and outlier points are computed by matplotlib's standard Tukey convention directly from that real data, not smoothed, binned, or approximated.
