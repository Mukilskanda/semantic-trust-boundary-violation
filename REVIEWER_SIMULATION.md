# Simulated IEEE Reviewer Feedback

Three independent review perspectives on `stbv_paper.tex` (the compressed, 7-page final version), simulating a conference program committee pass.

---

## Reviewer 1 — Novelty

**Major strengths.** The Semantic Trust Boundary framing is a clean, well-motivated gap statement: existing V2X trust stacks genuinely don't touch content. The provable-conservatism property (fusion can only escalate, never relax) is a real theoretical contribution distinguishing this from ad-hoc score-averaging fusion elsewhere in the literature. The CARLA synthesizer bug-and-fix narrative (§VI.D) is an unusually honest and useful contribution — most papers would either not run a live simulator at all, or would quietly fix the bug and only report the "good" numbers.

**Major weaknesses.** The core architectural claim ("combination and domain application, not a new mechanism") is honestly stated but is also this paper's biggest novelty risk — a reviewer skeptical of incremental-combination papers will ask why this clears the bar. No individual component (PKI, MBD, DS/Yager fusion, fine-tuned classifier) is new.

**Likely questions.** "What would a reviewer familiar with Zhang et al.'s CP-fabrication work (USENIX) say distinguishes your text-attack threat model from theirs at the mechanism level, not just the object/text distinction stated in one sentence?" "Is the Semantic Trust Boundary concept falsifiable, or is it a relabeling of 'the classifier's job'?"

**Specific improvements.** Add one concrete example contrasting a CP-fabrication attack and an STBV attack on the *same* message to make the object/text distinction visceral rather than asserted. Consider whether the "Semantic Trust Boundary" terminology needs to be introduced with a formal definition (currently informal prose) to survive a terminology-precise reviewer.

---

## Reviewer 2 — Methodology

**Major strengths.** The train/eval separation is unusually rigorous: v2.5b is verified template-disjoint via three independent signals (exact-text, template-id, 4-gram containment) against both the training corpus and the training-augmentation corpus, and this is stated with actual numbers, not just asserted. The true-adapter-resume continuation (vs. reinit-from-scratch) is methodologically correct and clearly distinguished from how prior checkpoints in the same lineage were produced. The theoretical propositions (P1–P6) are proved from the actual implementation, not from Yager's rule in the abstract — a distinction the paper is careful to state.

**Major weaknesses.** The freeze audit (companion document) discloses that Table I's B3-dependent rows (STBV-Bench v1 ablation) were **not** independently re-run against the final checkpoint in this pass. This is a real methodological gap: the paper's headline F1=0.995 number may not describe the exact checkpoint characterized everywhere else in the paper. Similarly, the adaptive-attack ASR (21.6%) is explicitly stated as measuring the *prior* checkpoint. A methodology-focused reviewer will flag that two of the paper's most load-bearing numbers are checkpoint-inconsistent with the rest.

**Likely questions.** "Table I and Table II report different checkpoints of the same architecture — how should a reader compare F1=0.995 (Table I) against F1=0.945 (Table II) if they're not the same model?" "Why wasn't the adaptive-attack campaign rerun given how central it is to the robustness claim?" "The CARLA run-to-run instability (§VI.D) undermines the interpretability of Table IV's single/dual-run numbers — why not run 5+ seeds as the deployment section of the prior paper draft did?"

**Specific improvements.** Rerun STBV-Bench v1's B3-alone and full-stack rows against the final checkpoint before submission (cheap, no new data needed — same fixed 10,000-message set, same eval harness). Rerun the adaptive-attack campaign against the final checkpoint, or explicitly retitle Table V "prior-checkpoint reference result" throughout, not just in the caption. Increase CARLA seeds/runs given the demonstrated instability, or explicitly bound the claim to "single-run illustrative, not a statistically characterized estimate."

---

## Reviewer 3 — Evaluation

**Major strengths.** This is the paper's clear strength: seven genuinely independent evaluation regimes (ablation, in-distribution, template-disjoint held-out, real kinematic attacks, live simulator, deployment replay, adaptive attacker), each answering a different, explicitly stated question, with results that disagree with each other in informative ways (e.g., v1's F1=0.995 vs. v2.5b's F1=0.945 vs. VeReMi's F1≤0.833) rather than being smoothed into one number. The CARLA bug-fix result is a genuinely rare and valuable evaluation-honesty contribution: most papers wouldn't have the live-simulator infrastructure to even discover this class of bug, let alone report it mid-evaluation.

**Major weaknesses.** Sample sizes for the live evaluations are small relative to the benchmark evaluations (CARLA n=400, SUMO n=2,000 vs. STBV-Bench n=10,000+), and CARLA's demonstrated non-determinism (§VI.D) means even that small n isn't a stable estimate. The paper is candid about this but a reviewer will still want to see whether the core CARLA finding (authority_override/false_hazard_clearance fixed, sybil/semantic_manipulation not) replicates at n>2 runs before treating it as settled. The VeReMi evaluation covers only 3 of the dataset's documented attack types (ConstPos, DataReplay, DoS) — the paper doesn't state why (e.g., RandomPos, GridSybil, DataReplaySybil are standard VeReMi Extension attack types not covered here).

**Likely questions.** "Why only 3 of VeReMi's ~7 attack types?" "Is the CARLA finding (2 attack types fixed, 2 still missed) stable at 5+ runs, matching the rigor of the architecture's earlier 15-run CARLA protocol?" "What is B3's false-positive rate specifically on the v2.5b benchmark broken out by attack family, given the aggregate F1 alone doesn't show whether the gap is uniform or concentrated?"

**Specific improvements.** State explicitly in the Methodology section why only 3 VeReMi attack types are covered (data availability in this environment) rather than leaving it implicit. Run CARLA at 5+ seeds matching the architecture's own established multi-run protocol, given the instability finding makes single/dual-run numbers hard to trust. Add a per-family breakdown for v2.5b (currently only aggregate F1 is reported) so a reader can see whether the improvement from continued fine-tuning is uniform or concentrated in a few families.

---

## Cross-cutting recommendation before submission

The single highest-priority fix identified by all three reviewers, independently, is the **checkpoint-consistency gap**: Table I (ablation) and Table V (adaptive attack) do not describe the same checkpoint as Tables II–IV. This should be resolved — by rerunning both against the final checkpoint — before the paper is considered submission-ready, even though neither rerun is required by a "bug" in the freeze-policy sense. See `READY_FOR_SUBMISSION.md` for this flagged as an open item.
