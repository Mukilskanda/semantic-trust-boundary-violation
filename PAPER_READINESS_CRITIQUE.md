# Part 13 — Reviewer Critique (Brutally Honest)

Written as a strict IEEE TDSC/TITS reviewer would, grounded ONLY in what the
repository and this evaluation cycle actually demonstrate — including the
unflattering findings the new framework surfaced. Scores are /10 for the
artifact **as it stands today**; parenthetical scores are what is realistically
reachable with the GPU runs + VeReMi importer + the identified fixes.

## Scores

**Novelty: 6/10 (reachable 7.5).** The STBV framing — semantic attacks that
survive crypto+behavioral+consistency layers — is a genuinely good angle, and
the two-stage flagship scenario is a compelling narrative device. But layered
trust stacks and DS-theoretic misbehavior fusion exist (Dietzel/Kargl 2014),
and LLM-based detection is crowded. Novelty survives only if the paper's
claims stay tightly scoped to the semantic-boundary class and the
conflict-aware fusion of an LLM evidence source; any broader claim will be
shot down in related work.

**Technical depth: 7/10.** The fusion layer is now mathematically honest
(Yager's rule, documented Zadeh-regime rationale, pignistic banding,
dogmatic-source analysis with regression tests — genuinely above the bar for
this literature). B1 is substantial. But: MBD is 351 lines with hardcoded
thresholds and a 5-message history horizon; CP is a 165-line heuristic whose
confidence conflates disagreement with sparsity (see Correctness); PKI is a
simulation. The stack's depth is very unevenly distributed and the paper must
not imply otherwise.

**Correctness: 5/10 (reachable 8).** The new evaluation framework immediately
found a real calibration flaw: **on self-generated benign dense traffic the
full stack REJECTs 37% of benign messages, and on replay scenarios FPR is
0.93** — because CP's cp_confidence drops in spatially spread (dense,
60m-spacing) traffic and the orchestrator's min() fold treats "low CP
corroboration" as "suspicious." A system whose FPR is 0.93 on a family it
nominally detects is not deployable and not publishable as-is. This is a
fixable calibration/semantics issue (CP low-confidence should raise
*uncertainty*, i.e. theta mass, not *disbelief* — the DS machinery to do this
correctly now exists in trust_engine/dempster_shafer.py), but it MUST be
fixed and re-measured before any performance claim is made. Credit: nothing
was hidden; the framework caught it; that's what the framework is for.

**Experimental validation: 4/10 (reachable 7.5).** Today: self-generated
synthetic scenarios only; B3 — the paper's centerpiece — has never been
evaluated end-to-end with real inference in any run I can verify (every
manifest in this cycle records b3_available=false). The full-vs-no_b3
McNemar comparison is currently meaningless and the framework says so.
Until (a) GPU runs produce real B3 columns and (b) at least VeReMi Extension
results exist, the experimental section cannot support the central claim.

**Evaluation methodology: 8/10.** This is now the artifact's strength:
seeded multi-run generation, 7 ablation configurations + 3 documented
baselines, per-message CSVs, FPR/FNR/detection-rate/caution-rate with the
CAUTION convention stated once and applied everywhere, applicability-guarded
statistics (McNemar exact-vs-chi2 switching, bootstrap CIs, refusing tests
where invalid), manifests with dataset SHA fingerprints. Missing for a 9+:
adaptive-attacker experiments and external-dataset results.

**Reproducibility: 8/10.** Manifests capture config/seeds/versions/hardware/
dataset hashes; scenario generation is deterministic per seed; every table is
regenerable by one command. Deductions: no CI pipeline in the repo, no
pinned requirements.txt with hashes, git commit is unrecorded when run from
a zip (the manifest flags this rather than faking it — good — but pin it).

**Writing readiness: 3/10.** No paper draft exists in the repo. The raw
materials (AUDIT_REPORT, LITERATURE_AND_DATASETS, auto-generated LaTeX
tables/figures) are strong inputs, but limitations text, threat model,
related-work differentiation, and the results narrative all remain unwritten
— correctly so, since the load-bearing numbers (GPU B3 runs, post-CP-fix
metrics, VeReMi results) don't exist yet.

**Overall publishability today: 4/10.** Not submittable: the centerpiece
layer is unexercised, the current measured FPR is disqualifying, and there
are no recognized-dataset results. **Realistic ceiling after the identified
work: 7–7.5/10** — a solid workshop-to-second-tier-journal artifact, with
top-tier possible only if the VeReMi results are strong AND an
adaptive-attacker study is added.

## Ordered fix list (highest leverage first)

1. **Fix CP-confidence semantics** (uncertainty, not disbelief — route
   cp_confidence into theta mass via the existing MassFunction machinery),
   then re-run `evaluation/run_experiments.py` full; FPR on benign must drop
   to near the caution-rate design intent. Everything else is blocked on
   trustworthy numbers.
2. **GPU runs** of run_experiments.py + validation/run_* (real B3 columns,
   real bridge_ms, real full-vs-no_b3 McNemar).
3. **VeReMi Extension importer** (~100 lines, build against real files) +
   the two canonical plausibility baselines from the VeReMi paper.
4. **Adaptive attacker study** (extend the B3/B6 paraphrase test into a
   real experiment).
5. Timestamp-semantics fix (S1 in AUDIT_REPORT) and regenerate fixtures.
6. requirements.txt with pins + CI (run the fast suites per commit).
7. Only then: write the paper.
