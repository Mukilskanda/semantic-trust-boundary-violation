# Layer (Responsibility) Matrix -- Scientific Audit

Reviewing `figures_generated/scripts/redesign_layer_responsibility.py` and the current `fig_layer_responsibility` as it appears in `stbv_paper.tex` (Section IV, Motivation for Multi-Layer Semantic Trust), before making any change.

## 1. What scientific question is this figure trying to answer?

Nominally: "which trust layer detects which class of threat, and does the fused architecture cover everything?" That is a legitimate, evidence-answerable question and matches the paper's central claim (Section IV: "no layer can answer another's question by construction").

## 2. Does the current figure answer that question clearly?

Not as clearly as it should. Three problems:

- The figure mixes two different things in one matrix: **layers** (B1, B2, CP, B3) and **the Trust Decision Engine**, which is not a detector but a fusion/decision stage -- putting it in the same "which layer detects what" grid implies it is a fifth parallel detector, which is not the paper's claim (its column is really "does the *fused* architecture cover this," a different question than the other four columns).
- Row labels encode *benchmark names* ("ITE-Bench B1-focused," "VeReMi ConstPos/DataReplay," "v2.5b," "CARLA sybil/semantic_manipulation") inside the axis label itself, which belongs in the caption, not the axis -- a reviewer has to parse benchmark provenance before even reading the matrix.
- The title ("Layer Responsibility Matrix") reads as an architectural/conceptual label, not an evaluation-figure label, and does not signal that every cell is measurement-derived.

## 3. Which parts look subjective?

The four-level ordinal scale (**Strong / Moderate / Weak / Not Exercised**) is the main issue. The script's own docstring defines these as "an ordinal summary of quantitative results," which is honest, but the boundary between "Weak" and "Moderate" is not derived from any stated threshold -- e.g., MBD's CARLA backstop and CP's "small marginal F1 gain" are both called "Moderate" despite being different in kind (one is a full detection backstop with 40/40 Reject; the other is a <1-point F1 delta), while B1's 0.143 recall and B3's snake-case-tag miss are both called "Weak" despite also being different in kind (a partial detector vs. a near-total miss on one sub-pattern). A reviewer cannot verify these four buckets from the text alone -- that subjectivity is the central defect this redesign should remove.

## 4. Which labels are unsupported by experimental evidence, specifically?

**One cell is now unsupported as a direct result of the immediately preceding pass's table redesign, and this audit is the first place that is flagged.** The current figure's Row 2 ("Behavioral/Kinematic") x B1 cell is labeled "Weak," sourced (per the script's original comment) to "B1's 0.143 on B2-focused attacks." That specific number (0.143) **no longer appears anywhere in the current manuscript text** -- the prior pass replaced the old `tab:ite_ablation` (which had a clean per-attack-class recall breakdown: Communication/Behavioral/Semantic x B1-only/B1+B2/Full-stack) with the new unified `tab:ablation`, which reports only *overall*, benchmark-wide Acc/Prec/Rec/F1/FPR per configuration -- not per-attack-class recall. The manuscript's own Finding paragraph (Section V-A) still gestures at a per-family breakdown ("1.000 on its own B1-native families, per-family breakdown below") but no table or figure currently in the paper carries that breakdown. **This is a real, current traceability gap**, not a hypothetical one -- addressed in Step 7's traceability table below by using only claims the current manuscript text actually states (the surviving sentence "every ITE-Bench-native family reaches 1.000 recall under its own layer and 0.000 under any other," Section V-A), rather than the specific 0.143 figure that is no longer in the paper.

Every other cell traces to text or a table still present in the manuscript (verified in the Step 7 traceability table).

## 5. Which text is unnecessarily long?

The row labels (e.g., "Behavioral / Kinematic\n(ITE-Bench B2-focused; VeReMi DataReplay/DoS)") mix an evaluation dimension with a citation, doubling as both an axis label and a footnote. The in-cell text ("Not Exercised" repeated 8 times across 20 cells) is the single largest source of visual clutter and repeated text the request specifically flags.

## 6. Would an IEEE reviewer immediately understand it?

Not immediately. A reviewer has to: (a) parse a benchmark citation embedded in each row label, (b) hold a four-level unlabeled ordinal scale in mind without a stated numeric threshold, and (c) figure out on their own that the "Trust Engine" column is answering a different question than the other four columns. All three are fixable without changing any underlying result.

## Conclusion

The figure's underlying intent is sound and the results it summarizes are real. The redesign in `LAYER_MATRIX_REDESIGN.md` (1) separates layers from the fusion column conceptually via a caption note rather than fixing this in the visual grid itself (kept as a column, since removing it would drop real, useful information -- but explicitly reframed in the caption as answering "does the fused system cover this," not "which detector caught it"), (2) moves benchmark names out of row labels into the caption, (3) replaces the four-level subjective scale with a 3-symbol scheme tied to an explicit, stated rule, and (4) relabels the one now-unsupported cell using only claims the current manuscript text actually makes.
