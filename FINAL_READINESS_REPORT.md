# Final Publication Readiness Report

A second, more critical pass, performed after all work in this round is
complete, as instructed. This report does not soften findings to make
the work appear more finished than it is.

## What was actually delivered this round

| Deliverable | File | Status |
|---|---|---|
| Related Work (10 subsections + comparison table) | `RELATED_WORK.md` | Real citations, single-session depth |
| Reproducibility + Parameter Appendix | `REPRODUCIBILITY_PARAMETER_APPENDIX.md` | Complete, includes a real disclosed gap (equations vs. code) |
| Semantic Transformation Engine Appendix | `SEMANTIC_TRANSFORMATION_APPENDIX.md` | Complete, two real worked examples |
| CP Validation | `CP_VALIDATION.md` | Complete, exhaustive search, quantitative result |
| 10 real data-grounded figures | `figures_v2/*.pdf`, `.png` | Complete for the plots requested; 4 architectural/workflow diagrams not produced (see below) |
| Expanded Discussion + Limitations (L12–L16) | `DISCUSSION_AND_LIMITATIONS.md` | Complete |
| Reviewer-Response Matrix | `REVIEWER_RESPONSE_MATRIX.md` | Complete, provenance of criticisms stated honestly |
| Updated manuscript LaTeX (Abstract, Sections I–V, References) | delivered in the prior conversation turn as a full code block, not re-pasted here | Complete as a standalone document; **not yet re-merged with this round's four new appendices into one final .tex** |

## What was NOT completed, and exactly why

1. **Related Work is single-session depth, not exhaustive.** A
   Transactions-quality related-work section for a security/ITS crossover
   paper typically reflects a systematic review across dozens of papers
   per subsection, cross-checked against recent Transactions issues
   directly (not just general web search) and refined over multiple
   passes. This round performed ten targeted searches and selected the
   strongest, most directly verifiable hits from each — real and honest,
   but a reviewer at a top venue will likely ask for more depth,
   particularly in §5 (semantic trust for V2X specifically), where
   directly-on-topic prior art is genuinely thin. This cannot be fully
   closed without either more search iterations or access to a
   citation database beyond general web search.

2. **Four requested figures were not produced**: a redrawn Motivation
   figure, a Vertical Architecture diagram, an STBV-Bench generation
   pipeline diagram, and an Experimental Workflow diagram. These are
   conceptual/architectural diagrams (boxes, arrows, layers), not data
   plots — producing them well requires deliberate diagram design
   (likely in a vector tool or TikZ), not the `matplotlib`-from-real-data
   approach used for the other ten. Fabricating placeholder diagrams
   would violate the non-negotiable rule against manufacturing figures;
   they are correctly left undone rather than faked.

3. **The manuscript has not been re-assembled as one final, integrated
   `.tex` file** incorporating this round's four new appendices
   (Related Work as Section II or a numbered section, the
   Reproducibility/Parameter/Semantic-Transformation appendices as
   formal LaTeX appendices, and the ten new figures embedded with
   `\includegraphics`). What exists is: (a) the corrected core manuscript
   (Abstract through Conclusion, References) delivered as LaTeX in the
   prior turn, and (b) this round's four new documents and figure set,
   each internally complete and cross-referenced by filename but not yet
   literally spliced into that `.tex` file's structure. This is a
   mechanical integration step, explicitly not attempted in this round
   given the volume of new content generated, and is the single largest
   remaining task before this is submission-ready as one document.

4. **No adaptive-attacker evaluation** (Limitation L14). This is
   flagged as requiring genuinely new research (an adversarial-search or
   red-teaming campaign against the deployed B3 checkpoint), not
   something achievable by re-analyzing existing repository outputs.

5. **No external semantic-attack corpus exists to validate against**
   (Limitation L12) — confirmed absent both in this repository and, as
   far as this round's literature search could determine, in the
   published literature generally. This is a field-level gap, not
   something this paper can close alone.

6. **Parameter sensitivity analysis has not been performed**
   (Limitation L13) — every fusion threshold is a fixed design constant;
   no sweep exists. This is achievable with existing repository code and
   data (re-running the ablation harness at different threshold values)
   and is the most tractable of the remaining gaps, but was not done
   this round given the volume of other work completed.

## Remaining weaknesses, stated plainly

- The manuscript, even after this round, reports a genuinely **modest**
  headline result (STBV-Bench v1 F1=0.718) alongside a demonstrably
  **worse** aggregate result under more realistic conditions
  (multi-vehicle F1=0.517) — this is scientifically honest but will read,
  to a reviewer skimming for a strong number, as a less impressive paper
  than one that reported only the higher figure. This is the correct
  trade-off per the mission's own non-negotiable rules, but it should be
  anticipated and explained proactively in the paper's own framing
  (Discussion, `DISCUSSION_AND_LIMITATIONS.md`) rather than left for a
  reviewer to discover unexplained.
- Cooperative Perception, a named architectural component with its own
  subsection in Section II, contributes **zero** measurable evidence to
  every benchmark in the paper. `CP_VALIDATION.md` explains this
  honestly, but a reviewer may reasonably ask why an entire architectural
  layer is included in the headline architecture diagram and equations
  while contributing nothing to any reported result — this is a
  structural tension in the paper's own framing that documentation alone
  cannot fully resolve; it may warrant either (a) explicitly scoping CP
  as "implemented and unit-verified, evaluation pending" in the abstract
  itself, or (b) completing the event-label generation work (L1) before
  submission so CP has at least one real, benchmark-scale result.
- The equations-vs-implementation gap (Section II's Eqs. 1/3/4 vs. the
  actual rule-based/DS-fusion code) is now disclosed rather than hidden,
  which is the right call — but a rigorous reviewer may still read
  Section II itself as somewhat overclaiming a formalized, tunable model
  where the real system is closer to a documented rule-based heuristic
  pipeline with a genuinely formal fusion step only at the final stage.
  Consider revising Section II's presentation (not its content) to
  frame Eqs. 1/3/4 explicitly as "conceptual" from the start, exactly as
  `REPRODUCIBILITY_PARAMETER_APPENDIX.md` §2 now recommends, rather than
  leaving that clarification to an appendix a reviewer might not read.

## Honest acceptance-probability estimates

These are qualitative, non-calibrated estimates based on typical scope
and rigor expectations at each venue, reasoned from the paper's current
state (strong empirical honesty and reproducibility; incomplete related
work depth; no adaptive-attacker evaluation; one architectural component
un-evaluated; manuscript not yet fully assembled). They are stated as
ranges, not point estimates, and are **not** inflated to make this report
more encouraging.

| Venue | Est. probability (current state) | Primary blocking factor(s) |
|---|---|---|
| **IEEE T-ITS** (Transactions on Intelligent Transportation Systems) | **15–25%** | Related Work depth; CP's zero-contribution status against a named architectural component; manuscript not yet assembled as one document; would likely go to a major-revision cycle rather than reject outright, given the empirical rigor and honesty already present |
| **IEEE TDSC** (Dependable and Secure Computing) | **8–15%** | No adaptive-attacker evaluation is a much more serious gap at a security-systems Transactions venue than at an ITS venue; reviewers here will expect a red-team/adversarial-robustness campaign, not perturbation-style robustness testing alone |
| **IEEE TIFS** (Information Forensics and Security) | **5–12%** | Same adaptive-attacker gap, compounded by TIFS's typical expectation of formal security analysis/guarantees, which this paper does not attempt (it is an empirical trust-architecture evaluation, not a security-proof paper) |
| **IEEE IV** (Intelligent Vehicles Symposium, conference) | **40–55%** | Conference bar is lower and more accepting of an honestly-scoped empirical study; the CP gap and related-work depth are less likely to be disqualifying at this venue, though still likely to draw reviewer comments |
| **IEEE ITSC** (Intelligent Transportation Systems Conference) | **45–60%** | Best fit of the five venues for this paper's current scope and rigor level; ITS-application-focused conferences generally reward exactly this kind of honestly-reported, reproducible empirical trust-architecture study |

**If the paper is not yet ready for the Transactions-tier venues** (it is
not, at the stated probabilities), **the specific, prioritized path to
improve those odds is**: (1) complete the manuscript assembly into one
`.tex` file with all appendices and figures integrated; (2) close the
parameter-sensitivity gap (L13) with a real threshold sweep, since this
is achievable with existing code; (3) either complete the CP event-label
generation work (L1) so CP contributes at least one real result, or
explicitly rescope the abstract/contributions list to describe CP as
"implemented and unit-verified, full-scale evaluation pending"; (4)
deepen Related Work §5 specifically; (5) if targeting TDSC/TIFS
specifically, add a genuine adaptive-attacker red-team evaluation — this
is the one item on this list that constitutes new research rather than
manuscript/repository work, and should be scoped as its own follow-on
effort, not squeezed into a documentation pass.
