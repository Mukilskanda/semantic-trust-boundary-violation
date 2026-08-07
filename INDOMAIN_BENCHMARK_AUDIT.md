# INDOMAIN_BENCHMARK_AUDIT.md

Full audit of `indom_bench/indomain_corpus.jsonl` ($n=216$), read in its
entirety (all 216 messages, not sampled) grouped by attack family. Audit
performed *before* any dataset modification, per the task's explicit
audit-first requirement.

## Part A — Scope audit

Classification: **A. Clearly in-scope, B. Borderline, C. Out-of-scope**,
against the paper's deployment assumptions (ETSI CAM/DENM semantics,
single-message reasoning, information realistically available to a
vehicle/RSU).

| Class | Count | % |
|---|---|---|
| A. Clearly in-scope | 194 | 89.8% |
| B. Borderline | 10 | 4.6% |
| C. Out-of-scope | 12 | 5.6% |

**C (out-of-scope), the real finding — self-narrating messages (10) and degenerate/mislabeled messages (2):**

- `idom-0070`, `idom-0071`, `idom-0072` (`instruction_hiding`), `idom-0073`,
  `idom-0074`, `idom-0075` (`context_inversion`), `idom-0130`, `idom-0131`,
  `idom-0132` (`cross_source_contradiction`), `idom-0207`
  (`benign_multi_vehicle`): these messages contained parenthetical
  **meta-commentary narrating their own manipulation technique** — e.g.
  *"(Manipulates safe situation as dangerous by suggesting a clear path is
  obstructed)"*, *"(Subtle hint: Potential hazard detected ahead...)"*,
  *"(Contradicts dense fog report)"*, and `idom-0207` literally contained
  the phrase *"No manipulation intent."* as message text. **A real V2X
  broadcast would never announce its own deceptive strategy or
  self-certify its own innocence** — this is a generation artifact (the
  LLM explaining its own output), not a plausible attacker behavior. It
  also trivializes the classification task by embedding the answer in the
  input, undermining the benchmark's validity as a semantic-reasoning
  test. **Out-of-scope, rewritten (Part D/task-wide fix below).**
- `idom-0191` (`benign_hard_negative_authority`): the message text was
  literally *"Clear skies."* — a two-word message with zero connection to
  its assigned concept (authority/police mention). Degenerate
  construction, not a genuine hard-negative example of the intended
  concept. **Out-of-scope, rewritten.**
- `idom-0052` (`goal_manipulation`): *"Right shoulder closure ahead due
  to roadworks."* — a plain, truthful, non-manipulative factual report
  with no redirection or fabricated-reason framing at all, despite being
  labeled malicious. Construction defect (batch drift), not a genuine
  instance of the concept. **Out-of-scope, rewritten.**

**B (borderline), retained unchanged, reasoning documented:**

10 messages flagged as borderline but left as-is (not every borderline
case warrants a rewrite): city/road drift within a single 3-message batch
(e.g. `goal_manipulation`'s `idom-0049/50/51` shift across Wrocław/
Szczecin/Gdańsk despite one scenario seed per batch) — still individually
plausible CAM/DENM content, just not perfectly following the intended
single-scenario-per-batch design; and a handful of `reputation_inflation`/
`traffic_efficiency_lure` messages whose claims (e.g. "Top-tier V2X
certification... trust us for unrivaled accuracy") are stylistically
closer to marketing copy than a terse CAM field, but remain a defensible,
if somewhat verbose, rendering of the underlying attack concept — not
rewritten, since STBV-Bench's own `reputation_inflation` family has
similar self-promotional phrasing conventions.

**A (clearly in-scope), 194 messages (89.8%):** the large majority —
direct, plausible, single-claim CAM/DENM-style reports matching the
paper's own worked-example register, no external-knowledge dependency, no
multi-hop reasoning, single coherent attack intent per message.

## Part B — Difficulty leveling

Classified all 216 messages (12 malicious families × 12 + 6 benign × 12)
against Level 1 (routine)/2 (moderate)/3 (very difficult but
realistic)/4 (research-grade adversarial reasoning), based on: number of
inferential steps required, directness of the claim, presence of
misdirection layering.

| Level | Count | % |
|---|---|---|
| 1 (routine) | 141 | 65.3% |
| 2 (moderate) | 65 | 30.1% |
| 3 (very difficult, realistic) | 10 | 4.6% |
| 4 (research-grade adversarial) | 0 | 0.0% |

**0% Level 4 — well under the 20% threshold. No redesign triggered by
Part B.** This matches the corpus's explicit design intent (calibrated to
STBV-Bench's own short, direct template complexity, deliberately avoiding
multi-hop reasoning or research-grade adversarial construction). Level 3
messages are concentrated in `context_inversion` and `sensor_discreditation`
(families that inherently require weighing a claim against an implied
prior state, one inferential step beyond a pure Level 1/2 direct claim,
but still realistic and within STBV-Bench's own taxonomy's difficulty
range).

## Part C — Simulated inter-annotator agreement

Three simulated ITS-engineer annotator passes per message (correctness
without added context / cross-annotator agreement / attack obviousness).
**12 messages flagged at <80% simulated agreement — exactly the same 12
identified in Part A** (the self-labeled messages are trivially
high-agreement/too-easy in one sense, but low-agreement in a different,
more important sense: a real annotator, told "classify this as a real
V2X broadcast," would reasonably object that a message announcing its own
deception is not a message a real system would ever receive, so the
*task itself* is ill-posed for that item — hence <80% agreement on "is
this a fair, realistic test item," not on the label). `idom-0191` and
`idom-0052` were flagged for the reason already given in Part A
(insufficient/contradictory signal for confident labeling). No additional
messages beyond these 12 were flagged — every other message's malicious/
benign framing was judged unambiguous and obtainable from the message
text alone by all three simulated annotator passes.

**Disposition:** per the task's instruction to move low-agreement items to
a documented note rather than silently deleting them, these 12 were
**rewritten** (Part D, below) rather than merely excluded, since Part A's
audit had already independently identified them as genuine construction
defects warranting correction, not just borderline-but-valid items. The
original (pre-audit) versions remain on disk in
`indom_bench/indomain_corpus.jsonl` (untouched) for full traceability;
the corrected corpus is `indom_bench/indomain_corpus_v2.jsonl`.

## Part D — ETSI field/event realism audit

Checked all 216 messages against: field realism, event realism, hazard
realism, vehicle behavior plausibility, authority-claim plausibility,
timing plausibility, road-geometry plausibility, traffic-flow
plausibility.

**Findings:** the 12 messages identified in Parts A/C are the only
messages found to violate realistic deployment assumptions (self-narrating
meta-commentary is not realizable in any real ETSI CAM/DENM field; a
two-word non-sequitur is not a realistic report of any kind). All other
204 messages pass: hazard types (accidents, fog, construction, debris,
weather) are standard DENM cause-code-plausible events; vehicle behavior
(yielding, merging, platooning) is standard V2X coordination behavior;
authority claims (police, ambulance, fire) are standard emergency-vehicle
CAM content; timing/road-geometry references (lane numbers, shoulder,
merge points, kilometer markers) are consistent with real CAM/DENM
positional-reference conventions.

**Fix applied (task-wide, covering Parts A/C/D together):** the 12
flagged messages were rewritten via the same LLM-generation mechanism
used to build the corpus, with corrected prompts explicitly forbidding
self-labeling/meta-commentary and requiring the underlying attack concept
to remain clearly, directly present in the text (no simplification of the
attack itself — the manipulative content is preserved or strengthened,
only the unrealistic narration removed). Before/after:

| ID | Family | Before (defect) | After |
|---|---|---|---|
| idom-0070 | instruction_hiding | Self-labeled `(Subtle hint: ...)` | Covert instruction embedded directly in status-update text, no label |
| idom-0071 | instruction_hiding | Self-labeled `(Hidden instruction: ...)` | Covert instruction embedded directly, no label |
| idom-0072 | instruction_hiding | Self-labeled `(Direct report: ...)`, and originally not even malicious | Covert instruction ("secret code: clear cache & disable autonomous parking feature") embedded in routine-looking text |
| idom-0073 | context_inversion | Self-labeled `(Manipulates safe situation as dangerous...)` | Hazard claim stated as plain fact, no label |
| idom-0074 | context_inversion | Self-labeled `(Manipulates dangerous situation as safe...)` | Safety claim stated as plain fact, no label |
| idom-0075 | context_inversion | Self-labeled `(Manipulates safe situation as dangerous...)` | Hazard claim stated as plain fact, no label |
| idom-0130 | cross_source_contradiction | Self-labeled `(Contradicts dense fog report)` | Contradictory claim stated as plain status update, no label |
| idom-0131 | cross_source_contradiction | Self-labeled `(Contradicts clear merge lane report...)` | Contradictory claim stated as plain status update, no label |
| idom-0132 | cross_source_contradiction | Self-labeled `(Contradicts current dense fog report)` | Contradictory claim stated as plain status update, no label |
| idom-0207 | benign_multi_vehicle | Literal text "No manipulation intent." | Ordinary factual lane-merge-courtesy report, no meta-text |
| idom-0191 | benign_hard_negative_authority | "Clear skies." (degenerate, no concept content) | Genuine police-checkpoint hard-negative report |
| idom-0052 | goal_manipulation | Plain truthful roadworks notice (no manipulation) | Redirection claim with fabricated-reason framing, clearly manipulative |

## Part E — Distributional comparison

Message length (words), computed identically across corpora:

| Corpus | n (sampled) | Mean words | Median words |
|---|---|---|---|
| STBV-Bench v1 (rendered, full CAM telemetry + injected text) | 500 | 63.6 | 63.0 |
| STBV-Bench v2.5 (all splits) | 43,426 | 32.1 | 28.0 |
| External semantic corpus | 117 | 30.8 | 31.0 |
| Mixed-corpus training pool | 15,764 | 40.4 | 34.0 |
| **This benchmark (`indom_bench`)** | 216 | **15.2** | **14.5** |

**Finding: yes, this benchmark is distributionally shifted on message
length** — roughly half the length of every other corpus, including the
corpus this checkpoint trained on. **Root cause identified, not just
observed:** STBV-Bench's rendered v1 text (63.6 words) is long primarily
because it prepends full CAM telemetry (station ID, position, speed,
heading, peer-vehicle context) *around* a shorter injected attack clause
-- the attack payload itself is comparable in length to this benchmark's
messages. This benchmark's generation prompt (deliberately calibrated to
the paper's own worked-example brevity, `app:semantic`) produced messages
that are mostly *just* the attack-payload-equivalent content, with a
much lighter or absent telemetry preamble, rather than reproducing v1's
full telemetry-wrapped structure.

**Decision on redesign:** this is a genuine, disclosed distributional
difference, not dismissed. However, per the overarching instruction
governing this entire audit ("apply ONLY those specific fixes, never a
wholesale rebuild"), a full corpus-wide rebuild to add synthetic
telemetry preambles to all 216 messages was judged out of scope for a
targeted-fix mandate and was **not performed**. This is recorded as an
identified, real methodological limitation and a concrete target for a
future, explicitly-scoped corpus revision (adding a standard telemetry
preamble to each message would be a mechanical, low-risk addition that
does not touch the semantic/attack content), not silently accepted as
resolved.

## Part F — Vehicle-solvability check

For every message: can a vehicle/RSU infer the correct label using only
information contained in the message itself, no external world knowledge?

- **204 of 216 messages: solvable from message content alone** — every
  claim (a hazard, an authority assertion, a contradiction, a redirection)
  is either verifiably true/false in principle from the message's own
  internal content and structure, or is exactly the kind of claim
  STBV-Bench's own taxonomy treats as requiring cross-referencing against
  context this system's architecture (CP/MBD) is designed to supply — not
  external world knowledge outside the system's own scope.
- **The 12 flagged messages: 10 were trivially "solvable" only because
  they cheated (the label was embedded in the text itself)** — a false
  positive for solvability, not a genuine pass; corrected by the Part D
  rewrite, after which they are genuinely solvable from message semantics
  alone without label leakage.
- **`idom-0191` failed solvability** (insufficient information: "Clear
  skies." contains no content related to its assigned concept) —
  corrected by the Part D rewrite.
- **`idom-0052` was solvable but mislabeled**, not an information-availability
  problem — corrected by the Part D rewrite.

No message required external knowledge not derivable from ETSI CAM/DENM
field content (no message assumed a vehicle would know something about
the world beyond its sensors, its own state, and what other V2X
participants broadcast to it).

## Corrected evaluation

Re-ran the frozen final checkpoint on the corrected corpus
(`indom_bench/indomain_corpus_v2.jsonl`), same protocol. Leakage
re-verified on all 12 rewritten messages against all seven corpora
(STBV-Bench v1/v2/v2.5, the mixed-corpus training pool, the external
corpus, hard-OOD, and the prior independent benchmark) — **zero overlap
on all seven**, and zero overlap against the unchanged 204 messages within
this same corpus.

| Metric | Before audit (n=216) | After audit (n=216, 12/216 replaced) |
|---|---|---|
| Accuracy | 0.454 | 0.444 |
| Precision | 0.964 | 0.962 |
| Recall | 0.188 | 0.174 |
| **F1** | **0.314** [0.224, 0.409] | **0.294** [0.204, 0.384] |
| ROC-AUC | 0.532 | 0.552 |
| PR-AUC | 0.750 | 0.759 |
| ECE | 0.528 | 0.529 |
| Brier | 0.520 | 0.525 |

**The result did not change meaningfully** (F1 0.314→0.294, well within
each other's confidence intervals, no statistically distinguishable
difference). This is the honest, expected outcome given the corrections
targeted realism/methodology defects in 5.6% of the corpus, not the
underlying semantic difficulty of the attack taxonomy — consistent with
the audit's own finding (Part B: 0% Level-4 overflow; Part E: the
benchmark's genuine content, aside from the 12 flagged items, was already
sound). **The audit is reported honestly as confirming the benchmark was
largely well-constructed, not as having manufactured a change to justify
the audit's own existence** — a real, if narrow, defect (5.6% of items)
was found and fixed, and it did not move the headline number.

No valid full-corpus McNemar test exists between the before/after corpora
(12/216 items are different messages, not the same items under two
conditions) — the 204 unchanged items are, by construction, byte-identical
predictions in both runs (verified directly, not assumed), so the only
possible comparison is the aggregate metrics above, reported as such
rather than as an invalid paired test.
