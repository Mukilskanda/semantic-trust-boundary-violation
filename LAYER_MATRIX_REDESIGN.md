# Layer Matrix Redesign

Redesign of `fig_layer_responsibility` per `LAYER_MATRIX_AUDIT.md`'s findings. No other figure was touched. No experimental result was changed; no new metric was computed. The figure file keeps its existing name and LaTeX label (`fig_layer_responsibility`) so no other part of the manuscript needed to change -- only the figure's own image and its own caption were edited.

## Title change adopted

Renamed, in the caption and the generating script's docstring, from **"Layer Responsibility Matrix"** to **"Layer-wise Threat Coverage Matrix"**, per the suggestion accompanying this request: the new title states what the figure evidences (coverage of threat classes, evidence-backed) rather than reading as a conceptual/architectural label. The LaTeX figure label (`fig_layer_responsibility`) was intentionally left unchanged, since renaming it would require touching every cross-reference to this figure elsewhere in the manuscript, which this task explicitly forbids ("do not modify any other part of the manuscript").

## What changed

1. **Rows**: replaced 4 long, benchmark-citing labels ("Cryptographic / Protocol\n(ITE-Bench B1-focused; VeReMi ConstPos)", etc.) with 4 short evaluation dimensions (Cryptographic Trust, Behavioral Trust, Semantic Trust, Deployment Robustness). Benchmark provenance moved entirely into the caption.
2. **Cells**: replaced the 4-level, unstated-threshold ordinal scale (Strong/Moderate/Weak/Not Exercised) with a 3-symbol, rule-stated scheme (✓ Validated / △ Partial / – Outside evaluation scope), with the complete decision rule given in both the script docstring and the caption -- no threshold is left implicit.
3. **Columns**: kept B1/B2/CP/B3/Trust Decision Engine (unchanged; removing a real column would drop real information), but added a visual separator (dashed rule) between the four detector columns and the Trust Decision Engine column, and the caption now states explicitly that the Engine's column answers a different question than the other four.
4. **One cell relabeled to remove an unsupported claim**: the old figure's Behavioral-Trust×B1 cell ("Weak," sourced to a 0.143 recall figure no longer stated anywhere in the current manuscript, per `LAYER_MATRIX_AUDIT.md` finding 4) is now "– Outside evaluation scope," which *is* fully supported by current manuscript text (Section V-A: "every ITE-Bench-native family reaches 1.000 recall under its own layer and 0.000 under any other" -- B1 reaching 0.000 on B2-native families is a real, currently-stated fact, correctly characterized as structural non-detection, not partial/weak detection).
5. **Visual design**: larger fonts (9pt axis labels, 16pt symbols vs.\ previous 6.6-8pt), equal cell sizes via `imshow` grid (unchanged mechanism, cleaner now that cell text is a single glyph, not a word), colorblind-safe 3-color palette (green/orange/light-grey, Okabe-Ito-derived, already the house palette), no repeated "Not Exercised" text (now a single "–" glyph), compact bottom legend replacing the previous colorbar-with-4-tick-labels.
6. **Grayscale safety**: verified each of the 3 symbols (✓/△/–) is unambiguous by shape alone, independent of the fill color, so the figure remains readable if printed in grayscale (the three fill colors also differ in lightness: green medium-dark, orange medium, grey light, providing a second independent cue).

## Step 7: full traceability table

Every cell in the redesigned matrix, and its exact source in the current manuscript.

| Row (dimension) | Column | Symbol | Source in current manuscript |
|---|---|---|---|
| Cryptographic Trust | B1 | ✓ | Section V-A: "every ITE-Bench-native family reaches 1.000 recall under its own layer" (B1-native = crypto/protocol families); `tab:ablation`'s "B1 only" row, Prec.\ 1.000 on ITE-Bench. |
| Cryptographic Trust | B2, CP, B3 | – | Same Section V-A sentence: "...and 0.000 under any other" -- B2/CP/B3 do not read certificate/protocol fields by construction (Section IV, per-layer walkthrough). |
| Cryptographic Trust | Trust Decision Engine | ✓ | `tab:ablation`'s Full STBV Framework / ITE-Bench row, F1$=0.945$, and Section V-A's McNemar result (full stack vs.\ B3-alone: 3,885 discordant, 0 reversed, $p{<}10^{-15}$) showing no cost to crypto-dimension performance from fusion. |
| Behavioral Trust | B2 | ✓ | Section V-A, same "1.000 recall under its own layer" sentence (B2-native = behavioral/kinematic families). |
| Behavioral Trust | B1, CP, B3 | – | Same sentence, "0.000 under any other"; B1/CP/B3 do not model per-sender history (Section IV). |
| Behavioral Trust | Trust Decision Engine | ✓ | `tab:ablation`'s Full STBV Framework / ITE-Bench row (F1$=0.945$, Rec.\ 1.000) and VeReMi Table~\ref{tab:veremi} (MBD detects real kinematic attacks with zero B3 contribution, Section V-C). |
| Semantic Trust | B3 | ✓ | `tab:ablation`'s "B3 only" row on STBV-Bench v2.5b, Rec.\ 0.999; Fig.~\ref{fig_attack_family_v25b}, recall 0.990-1.000 across all 13 real attack families. |
| Semantic Trust | B1, B2 | – | `tab:ablation`'s footnote: "v2.5b is a semantic-only benchmark by construction... B1 and B1+B2 would trivially score 0.000 recall." |
| Semantic Trust | CP | – | Section V-A / Limitations: CP's zero contribution is a disclosed data-generation gap (the semantic-attack generator never populates the `event` field CP's gate requires), confirmed identical on both ITE-Bench and v2.5b. |
| Semantic Trust | Trust Decision Engine | ✓ | `tab:ablation`'s Full STBV Framework rows on both benchmarks (F1$=0.877$ v2.5b, F1$=0.945$ ITE-Bench). |
| Deployment Robustness | B1 | – | No live-CARLA scenario (`tab:carla`) specifically targets B1's crypto/protocol checks; the 10 CARLA scenarios are semantic and behavioral by design (Section V-C). |
| Deployment Robustness | B2 (MBD) | ✓ | `tab:carla`: \texttt{sybil\_attack} and \texttt{semantic\_manipulation} both reach "40/40 Reject (MBD)" -- a clean, ceiling backstop result attributable specifically to MBD. |
| Deployment Robustness | CP | – | `tab:carla` reports no CP-specific outcome; CP requires peer reports not isolated in the CARLA scenario set (same data-generation gap as above). |
| Deployment Robustness | B3 | △ | `tab:carla`: \texttt{authority\_override}/\texttt{false\_hazard\_clearance} reach \texttt{MALICIOUS}+Reject (a real success), but \texttt{sybil\_attack}/\texttt{semantic\_manipulation} remain \texttt{BENIGN} to B3 -- "a genuine gap on raw snake-case event tags" (Section V-C) -- real, disclosed, partial, not ceiling. |
| Deployment Robustness | Trust Decision Engine | △ | `tab:carla` shows 4/6 attack scenarios at clean 40/40 Reject, but the same paragraph discloses a reproducibility caveat ("benign-scenario decisions varied materially between runs... CARLA's traffic manager not being seeded for exact decision randomness") -- real, disclosed, not an unqualified ceiling result. |

## Confirmation

Every cell above cites a specific sentence or table currently present in `stbv_paper.tex`. No cell relies on a number that does not currently appear in the manuscript (the one cell that previously did -- Behavioral Trust × B1 -- was relabeled, not left inconsistent). No experiment was rerun; no metric was invented.
