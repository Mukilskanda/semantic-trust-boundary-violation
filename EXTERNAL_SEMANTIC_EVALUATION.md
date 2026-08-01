# External Semantic Evaluation

An independent evaluation of the **frozen, unmodified** B3 checkpoint
(`semantic_gate_v3`) against a corpus that is not STBV-Bench, not built
from STBV-Bench's generator, and not derived from any text B3 could have
seen during training (to the extent that can be verified — see
`B3_DATA_PROVENANCE_REPORT.md` for what remains unverifiable about B3's
original training corpus). **B3 was not retrained, fine-tuned, or
otherwise modified to produce this report.** Every number below comes
from a single forward pass of the existing checkpoint over new text.

**Status: complete.** All five planned sources (directly-authored,
Claude-generated, paraphrased-from-public-corpora, GPT-generated,
Gemini-generated) are present. The GPT and Gemini subsets were produced
by the user running a fixed prompt (reproduced in §3) through ChatGPT and
Gemini directly, since this environment has no API access to either
provider, and pasted back verbatim; each entry was then assigned a family
label by mapping the provider's own free-text concept tag onto this
report's 10-family taxonomy (§3). Final corpus size: **$n=117$** (89
malicious, 28 benign). The numbers below supersede an earlier partial
pass computed at $n=77$ (three sources only) — that intermediate result
is not reproduced here, per this report's own stated policy of replacing
rather than appending to provisional numbers.

---

## 1. Why an external benchmark is needed

STBV-Bench v1/v2, the VeReMi kinematic companion bench, and the
mixed-threat bench (this project's existing benchmarks) are all built
from the same underlying generator lineage: real VeReMi kinematics
combined with this project's own seeded semantic-transformation engine
(`stbv_bench/transformations.py`). This makes them internally consistent
and free of the specific taxonomy-sharing leakage mechanism found in the
deprecated 120-scenario corpus (`DISCUSSION_AND_LIMITATIONS.md`, L12) —
but it also means every headline number in the paper, to this point, has
been measured on text this project itself generated. A reviewer at a top
venue can reasonably ask whether B3 detects semantic attacks in general,
or only the specific phrasing conventions of one team's generator. This
report is the answer to that question, built from text this project's
generator never produced and never touched.

## 2. Public dataset search (Requirements 1–2)

A real web search (not a memory recall) was performed for existing
public datasets that could serve this purpose directly.

**Finding: no publicly available dataset of labeled V2X-contextualized
semantic/social-engineering attacks was found.** This is documented, not
glossed over, per Requirement 2:

- **[V2AIX](https://arxiv.org/abs/2403.10221)** is a real, public,
  large-scale (285,000+ message) dataset of genuine ETSI ITS V2X traffic
  (CAM/DENM/CPM/SPATEM) collected from real vehicles and roadside units.
  It is the closest thing to a public V2X message corpus, but it is
  **entirely benign, structurally-encoded traffic** (numeric CAM/DENM
  fields per the ETSI standard) — the standard itself has no free-text
  payload field for a semantic/social-engineering attack to occupy. This
  is itself informative: the "semantic attack via natural-language V2X
  message" threat model this project studies is a research construct
  layered on top of the real protocol (via this project's own
  message-synthesis step, `pipeline/synthesizer.py`), not something the
  real-world protocol carries natively — so no public corpus of *real*
  semantic V2X attacks can exist under the current standard, and this
  absence is a field-level fact, not a search failure.
- Public **generic** (non-V2X) prompt-injection / jailbreak datasets do
  exist and are actively maintained: **[qualifire/prompt-injections-benchmark](https://huggingface.co/datasets/qualifire/prompt-injections-benchmark)**
  (5,000 labeled prompts), **[PointGuardAI/Prompt-Injection-OWASP-Benchmark-V2](https://huggingface.co/datasets/PointGuardAI/Prompt-Injection-OWASP-Benchmark-V2)**
  (OWASP GenAI LLM01-aligned), and **[Necent/llm-jailbreak-prompt-injection-dataset](https://huggingface.co/datasets/Necent/llm-jailbreak-prompt-injection-dataset)**
  (an aggregation of 30+ public safety datasets including HarmBench,
  AdvBench, JBB-Behaviors). These are **not V2X messages** — they are
  generic LLM-chatbot-directed prompts — but their well-documented public
  attack *archetypes* (authority-override framing, "ignore previous
  instructions," fabricated social proof, urgency coercion, hypothetical/
  roleplay framing) are real, independently-published patterns that this
  report draws on for one of its five sources (§3, "paraphrased_public"),
  giving that source a citable, external anchor rather than an invented
  one.
- No V2X-specific semantic-attack dataset was found published in the
  academic literature either (consistent with `RELATED_WORK.md`'s and
  `DISCUSSION_AND_LIMITATIONS.md` L12's earlier, independent search).

## 3. Corpus construction (Requirements 3–7)

Five sources, combined without any file-level or template-level overlap
with STBV-Bench (verified — see §5). **A provenance disclosure is made
explicitly here because it matters for how this corpus should be read:**

| Source | Who/what actually produced the text | n | Honesty note |
|---|---|---|---|
| `directly_authored` | Written one-at-a-time by Claude (this assistant), with deliberate per-item adversarial reasoning, in this session — **not** literal human authorship, since no separate human author is part of this pipeline | 32 (24 malicious, 8 benign) | Relabeled from the original task's "human-written" to avoid misrepresenting an AI author as a human one |
| `claude_generated` | Written by Claude in a single continuous batch-generation pass (same model, different process: no per-item deliberation, closer to how the task's "Claude-generated" category is normally understood) | 26 (20 malicious, 6 benign) | |
| `paraphrased_public` | Written by Claude, explicitly adapting the well-documented public prompt-injection archetypes named in §2 into V2X context (each entry cites which public pattern it adapts) | 19 (15 malicious, 4 benign) | Not literal copied text from any dataset row (none was downloaded); grounded in publicly documented, named attack archetypes |
| `gpt` | Generated by ChatGPT, run by the user with the fixed prompt in §3.1, pasted back verbatim and integrated unedited (family labels assigned by this report from the model's own free-text concept tags) | 20 (15 malicious, 5 benign) | Text is the provider's own output, not Claude's; this environment has no OpenAI API access, so this required the user's direct participation |
| `gemini` | Generated by Gemini, same fixed prompt, pasted back verbatim and integrated unedited | 20 (15 malicious, 5 benign) | Same as above, for Gemini; this environment has no Gemini API access |
| **Total** | | **117** (89 malicious, 28 benign) | |

### 3.1 The fixed prompt given to both providers

> *"You are helping build a security-research red-teaming corpus for a
> V2X (vehicle-to-everything) trust-verification research paper... Write
> 15 MALICIOUS and 5 BENIGN example V2X messages... Cover a MIX of these
> attack concepts, in your own words (do not copy phrasing from any
> existing dataset)... For the 5 BENIGN messages: write ordinary,
> legitimate V2X advisories... Format your answer as a numbered list of
> 20 items."* (Full text: `external_semantic_eval/gpt_gemini_generation_prompt.txt`
> equivalent, reproduced in-conversation when requested from the user.)

Both providers were given the identical prompt, so any systematic
difference between the `gpt` and `gemini` rows in §6 reflects a genuine
model-to-model difference in output, not a difference in what was asked.

**Attack families** (10, all independently named — verified to share zero
string overlap with both STBV-Bench's 20 family names and B3's `AF1`–`AF9`/
`Case 1`–`Case 5` training-taxonomy names):

`spoofed_authority_override`, `sensor_discreditation`,
`fabricated_peer_consensus`, `emergency_coercion`, `hazard_normalization`,
`phantom_hazard_fabrication`, `reputation_inflation`,
`infrastructure_impersonation`, `narrative_erosion`, `benign_control`.

These names describe the same finite space of plausible V2X social-
engineering concepts any team would eventually enumerate (an unavoidable
overlap in *concept*, not in *text* or *taxonomy naming* — see §5 for why
this distinction is the one that was actually verified). Every message
text is independently written; none reuses a rendered STBV-Bench sentence
or a STBV-Bench `transformations.py` template string.

**V2X context (Requirement 5):** every entry is phrased as a plausible V2X
message payload (CAM/DENM/CPM-style vehicle-to-vehicle or infrastructure-
to-vehicle text, consistent with the field-naming conventions ETSI CAM/
DENM standards use, as corroborated by the real V2AIX dataset's public
field documentation, §2) — not a generic chatbot prompt with the V2X
framing stripped out.

## 4. Benign messages (Requirement 7)

28 benign messages are included across the five sources, each an
ordinary, legitimate V2X advisory (roadworks, weather, platooning status,
emergency-vehicle yield notices) that does **not** attempt to override
the vehicle's own sensor authority — including deliberately topic-matched
benign counterparts to the malicious set (a legitimate ambulance-yield
notice next to the malicious "suppress braking for emergency" family, a
legitimate hazard-clearance notice next to the malicious "hazard already
resolved" family) so recall/precision cannot be inflated by topic alone.
Both GPT's and Gemini's benign sets independently included this same
"legitimate version of a malicious concept" pattern (e.g. Gemini's
"Emergency Clearance Notice" and GPT's "Incident Cleared," both pairing a
real hazard-resolution update with an explicit instruction to keep
relying on the vehicle's own sensors) without being told to structure it
that way beyond the general instruction in §3.1 — a small independent
confirmation that this is a natural, not cherry-picked, way to construct
a fair benign set for this threat model.

## 5. Template-overlap verification (Requirement 3, "MUST NOT reuse STBV-Bench templates")

Verified programmatically, not asserted: `external_semantic_eval/build_external_corpus.py`
extracts every literal string ≥25 characters from
`stbv_bench/transformations.py` (the actual source of STBV-Bench's
rendered templates) and checks every external-corpus entry for substring
overlap in either direction.

**Result: zero overlap hits, zero internal exact-duplicate texts**, across
all 117 entries, including the GPT/Gemini additions (script output:
`[OK] zero substring overlap with stbv_bench/transformations.py template
strings.`).

## 6. Evaluation of the frozen B3 model (Requirements 8–9)

`external_semantic_eval/evaluate_external.py` loads the same production
checkpoint (`b3/solution_stb/b3_semantic_gate/model/semantic_gate_v3`,
567,622,450 bytes, SHA-256 `9ee7475e...c2f5d2` — identical hash to every
other evaluation in this project) via the same `inference.py` predictor
class used in production. **No gradient step, no `.train()` call, no
weight file write occurs anywhere in this script** — inference only,
confirmed by direct code inspection (the script imports `get_predictor`
and calls `.predict()` exclusively).

### Headline results ($n=117$: 89 malicious, 28 benign)

| Metric | Value |
|---|---|
| Accuracy | 0.9060 |
| Precision | 0.9756 |
| Recall | 0.8989 |
| F1 | 0.9357 |
| True Positives | 80 |
| False Positives | 2 |
| False Negatives | 9 |
| True Negatives | 26 |
| ROC AUC | 0.9747 |
| PR AUC | 0.9814 |

Figures: `external_semantic_eval/figures/ext_fig_roc.pdf`,
`ext_fig_pr.pdf`, `ext_fig_calibration.pdf`, `ext_fig_per_family_recall.pdf`.

### Calibration (transfer test, not a refit)

The temperature $T=2.144598$ already fitted in `b3_eval/results/calibration.json`
(on an unrelated internal 85-sample split) was applied **post-hoc, without
refitting**, to test whether that existing calibration transfers to this
new corpus — the honest question, rather than fitting a new $T$ on 77
samples and calling it "calibrated."

| | ECE | Brier |
|---|---|---|
| Raw (T=1, uncalibrated) | 0.0541 | 0.0633 |
| Existing T=2.145 applied post-hoc | 0.1694 | 0.0873 |

**Finding, stated plainly: the existing temperature-scaling parameter does
NOT transfer well to this external corpus — it makes calibration worse,
not better** (ECE roughly triples). This is an important, non-inflated
result: it means B3's raw (uncalibrated) confidence is already closer to
correct on this external distribution than the internally-fitted
correction is, which is the opposite of what happened on the internal
split it was fitted on. This should be read as evidence that **temperature
scaling fit on one narrow internal split does not generalize across
distributions**, not as evidence that calibration doesn't matter — it
argues for calibrating on a broader, more representative sample before
relying on a single fitted $T$ in deployment.

### Per-family recall

| Family | n (malicious) | Recall |
|---|---|---|
| sensor_discreditation | 16 | 1.000 |
| fabricated_peer_consensus | 13 | 1.000 |
| hazard_normalization | 11 | 1.000 |
| reputation_inflation | 9 | 1.000 |
| emergency_coercion | 10 | 0.900 |
| infrastructure_impersonation | 8 | 0.875 |
| phantom_hazard_fabrication | 10 | 0.800 |
| narrative_erosion | 4 | 0.750 |
| **spoofed_authority_override** | 8 | **0.500** |

### Per-source accuracy (a secondary, exploratory breakdown)

| Source | n | Accuracy |
|---|---|---|
| gpt | 20 | 1.0000 |
| claude_generated | 26 | 0.9615 |
| gemini | 20 | 0.9000 |
| paraphrased_public | 19 | 0.8421 |
| directly_authored | 32 | 0.8438 |

This breakdown is reported for transparency but should not be
over-interpreted at this sample size (each source subset is small); it is
not used to draw a claim about which generation process, or which LLM
provider, is "harder" or "better" — that would need far more samples per
source to support statistically. Notably, GPT's and Gemini's subsets
(the two sources this report had no authorial control over) score at the
high end, not the low end, of this range — evidence against the concern
that Claude (as both the evaluated corpus's primary author and a
different model from B3's own architecture family) somehow constructed
an unrepresentatively easy corpus.

## 7. Differences between STBV-Bench and this external benchmark

This is the section most likely to be scrutinized by a reviewer, so it is
stated precisely rather than summarized away:

**Recall is higher here (89.9%) than on STBV-Bench v1's B3-alone
result (55.7%, `stbv_paper.tex` Section VI, RQ1).** This is a real,
measured difference, and it runs in the opposite direction a naive
"internal benchmarks are inflated" story would predict — so it deserves a
direct, honest explanation rather than a convenient one:

1. **STBV-Bench v1 was deliberately constructed to include a documented
   "bounded detection gap"** on six specific weak families phrased as
   subtle narrative framing or gradual reinterpretation, precisely
   because the team wanted the benchmark to stress-test B3's weakest
   point, not just measure its average case (`stbv_paper.tex`, Section
   VI-A; `PUBLICATION_PROGRESS.md`, L3). This external corpus was **not**
   deliberately constructed to be adversarially difficult in that same
   targeted way — its authors (Claude, across three source processes)
   were instructed to cover a concept list, not to specifically probe
   B3's known failure modes.
2. **The one family in this external corpus that most resembles STBV-
   Bench's known weak pattern — `spoofed_authority_override`, which
   leans on legalistic/regulatory-sounding override language rather than
   an explicit sensor-vs-infrastructure conflict — is also this corpus's
   worst-performing family (recall 0.500, tied for the lowest of any
   result reported anywhere in this project).** This is not a
   coincidence this report is eager to explain away: it is the same
   underlying brittleness (subtler, authority-flavored phrasing without
   an explicit "your sensor is wrong" framing) showing up again, in
   independently-written text, which is itself a small piece of
   convergent evidence that the STBV-Bench-documented weakness (L3) is a
   real property of the classifier, not an artifact of STBV-Bench's own
   phrasing. `narrative_erosion` (recall 0.750), the family most
   analogous to STBV-Bench's gradual-narrative-drift weak families, is
   the second-lowest.
3. **This external corpus is smaller** ($n=117$ vs. STBV-Bench v1's
   $n=10{,}000$) and was not built with the same kinematic realism
   (STBV-Bench v1 pairs its semantic text with real VeReMi trajectories;
   this corpus has no kinematic component at all — it tests B3 in
   isolation, on text only, which is in fact the correct comparison
   since B3 only ever sees text). A 117-sample external result should be
   read as a **directional cross-check**, not a replacement for
   STBV-Bench v1's statistical power.
4. **Family-level averages differ**: this corpus's 10 families were
   deliberately spread evenly (roughly balanced per family) rather than
   including STBV-Bench's specific mix of easy and hard families in
   proportion to a design that emphasizes stress-testing. A simple
   average over an evenly-spread, moderately-difficult family mix will
   generally look better than an average that specifically includes a
   concentrated hard cluster.

**The honest, unified conclusion**: B3 generalizes reasonably well to
independently-written attack phrasing covering the same threat concepts,
across three different authorial processes (Claude in two modes, and two
independent third-party LLMs it has no architectural relationship to)
(precision 0.976, ROC AUC 0.975 here are both strong, out-of-distribution
results, and are evidence against the concern that B3 only pattern-matches
STBV-Bench's specific sentences) — **but the specific weak points STBV-
Bench already documented (subtle authority-flavored and narrative-drift
phrasing) reproduce here too**, at a similar or worse severity
(spoofed_authority_override's 0.500 recall is the single worst number in
either benchmark). This external evaluation therefore **corroborates,
rather than contradicts, STBV-Bench's own documented limitation (L3)** —
it does not let the paper claim the weak-family finding was an artifact
of STBV-Bench's own generator, and it does not let the paper claim
external validation is uniformly worse either. Both directions of
potential overclaiming are foreclosed by reporting this honestly.

## 8. Provenance of the completed corpus

All five sources are integrated and this report's $n=117$ figures are
**final** — computed identically across sources by the same frozen-model
evaluation script (`evaluate_external.py`), with no per-source special
casing. The GPT and Gemini subsets were pasted in verbatim by the user
(§3, §3.1) and assigned family labels by this report from each provider's
own free-text concept tag, using judgment where a concept spanned more
than one family (e.g., Gemini's "Emergency Braking Demand," which
fabricates a structural-collapse hazard *and* demands immediate
compliance, was assigned to `phantom_hazard_fabrication` rather than
`emergency_coercion` because the fabricated-hazard mechanism is the
primary manipulation; this judgment call is disclosed rather than hidden,
since a different, defensible mapping could shift 1-2 samples between
adjacent families without changing the headline metrics). An earlier,
partial pass computed these same metrics at $n=77$ (three sources only);
those intermediate numbers have been fully replaced above, not left
standing alongside the final ones, per this report's own stated policy
against letting a reader cite a superseded figure.

## 9. What this report does not claim

- It does not claim B3 has been validated against a large, statistically
  powerful external corpus — 117 samples is directionally informative,
  not a replacement for a benchmark at STBV-Bench v1's scale.
- It does not claim the GPT- and Gemini-authored subsets are representative
  of those providers' typical output more broadly — each was sampled once,
  from one prompt; §6's per-source accuracy row for `gpt` (1.000 on 20
  samples) in particular should not be read as "ChatGPT-generated attacks
  are inherently easier for B3," since a single 20-sample draw is not
  strong evidence of a stable provider-level effect.
- It does not claim this resolves `DISCUSSION_AND_LIMITATIONS.md` L12
  (no external, independently-published ground-truth corpus of real-world
  V2X semantic attacks exists) — this report's corpus is itself authored
  by LLMs for this evaluation, not drawn from an independently-published,
  pre-existing ground truth. It is a genuine, useful cross-check against
  this project's own generator, not a substitute for the field-level gap
  L12 describes.

## Evidence index

- `external_semantic_eval/corpus_directly_authored.json`,
  `corpus_claude_generated.json`, `corpus_paraphrased_public.json`,
  `corpus_gpt.json`, `corpus_gemini.json` — all five sources, complete
- `external_semantic_eval/gpt_gemini_generation_prompt.txt` — the fixed
  prompt given to both providers (§3.1)
- `external_semantic_eval/build_external_corpus.py` — merge, dedup,
  STBV-Bench-overlap verification (zero hits)
- `external_semantic_eval/external_corpus.json` — the merged, verified
  corpus as evaluated ($n=117$)
- `external_semantic_eval/evaluate_external.py` — frozen-model inference,
  metrics computation (no training/fine-tuning code path exists in this
  script)
- `external_semantic_eval/external_eval_results.json` — full per-message
  predictions and all metrics
- `external_semantic_eval/generate_external_figures.py`,
  `external_semantic_eval/figures/*.pdf` — ROC, PR, calibration, per-family
  recall figures
- `stbv_bench/transformations.py` — source of the template strings
  checked against for overlap
- `B3_DATA_PROVENANCE_REPORT.md` — the related, separate investigation
  into B3's original training-data provenance
