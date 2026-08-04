#!/usr/bin/env python3
"""
validation/agreement_analysis.py
=================================
Computes inter-annotator agreement and human-vs-generator label validity
for the STBV-Bench human-validation study, then writes
`validation/validation_report.md`.

INTEGRITY GUARANTEE. This script will NOT invent, impute, or default any
annotation. If the annotator files are missing, blank, or only partially
filled, it writes a report containing clearly-marked PLACEHOLDERS and exits
without producing any numbers. There is no code path in this file that
generates a label.

Run:
    python validation/agreement_analysis.py
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
MASTER = HERE / "validation_sample.csv"
ANN = {a: HERE / f"annotation_template_annotator_{a}.csv" for a in ("A", "B")}
REPORT = HERE / "validation_report.md"
METRICS = HERE / "agreement_metrics.json"

VALID = {"malicious", "benign"}


def load_annotations(path):
    """Returns (labels_by_item, n_filled, n_total, malformed)."""
    if not path.exists():
        return None, 0, 0, []
    labels, malformed, total = {}, [], 0
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            iid = (row.get("item_id") or "").strip()
            if not iid:
                continue
            total += 1
            raw = (row.get("label") or "").strip().lower()
            if not raw:
                continue
            if raw in ("m", "mal", "malicious", "1", "attack"):
                labels[iid] = "malicious"
            elif raw in ("b", "ben", "benign", "0", "clean"):
                labels[iid] = "benign"
            else:
                malformed.append((iid, raw))
    return labels, len(labels), total, malformed


def cohens_kappa(a, b, items):
    """Unweighted Cohen's kappa for two raters over a shared item set."""
    n = len(items)
    if n == 0:
        return None, None, None
    obs = sum(1 for i in items if a[i] == b[i]) / n
    cats = sorted(VALID)
    pa = Counter(a[i] for i in items)
    pb = Counter(b[i] for i in items)
    exp = sum((pa[c] / n) * (pb[c] / n) for c in cats)
    kappa = (obs - exp) / (1 - exp) if (1 - exp) > 1e-12 else float("nan")
    return kappa, obs, exp


def prf(truth, pred, items, positive="malicious"):
    tp = sum(1 for i in items if pred[i] == positive and truth[i] == positive)
    fp = sum(1 for i in items if pred[i] == positive and truth[i] != positive)
    fn = sum(1 for i in items if pred[i] != positive and truth[i] == positive)
    tn = sum(1 for i in items if pred[i] != positive and truth[i] != positive)
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    acc = (tp + tn) / len(items) if items else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": p, "recall": r, "f1": f1, "accuracy": acc}


def kappa_interpretation(k):
    if k is None:
        return "n/a"
    for lo, txt in [(0.81, "almost perfect"), (0.61, "substantial"),
                    (0.41, "moderate"), (0.21, "fair"), (0.0, "slight")]:
        if k >= lo:
            return txt
    return "poor (worse than chance)"


def write_placeholder(status_lines, manifest):
    per_fam = manifest.get("per_family", {})
    fam_rows = "\n".join(
        f"| `{fam}` | {d['n']} | {d['mal']} | {d['n']-d['mal']} |"
        for fam, d in sorted(per_fam.items()))
    REPORT.write_text(f"""# STBV-Bench Human Validation — Report

> ## ⚠ STATUS: AWAITING HUMAN ANNOTATION — NO RESULTS IN THIS REPORT
>
> Every agreement and validity number below is a **PLACEHOLDER**. No
> annotations have been collected, and this pipeline does not and will not
> generate them. Do **not** cite any figure from this file until it has been
> regenerated from real completed annotator files.

## 1. Why this study exists

STBV-Bench's ground-truth labels are assigned by the same seeded generator
that produces the message text. No independent check currently establishes
that a message labelled `malicious` reads as malicious to a competent human
annotator, or that a `benign_control` message reads as benign. Without that
check, a detector "miss" cannot be distinguished from a mislabelled item,
and the benchmark's headline precision/recall inherit that ambiguity.

## 2. Sampling methodology

- **Population:** the {manifest.get('n_population', 'N/A'):,}-message slice of STBV-Bench v1 evaluated in the paper.
- **Sample size:** {manifest.get('n_sampled', 'N/A')} messages.
- **Strategy:** {manifest.get('strategy', 'N/A')}
- **Seed:** `{manifest.get('seed', 'N/A')}` (deliberately distinct from the modelling seed 42).
- **Families covered:** {manifest.get('n_families', 'N/A')} of 21.
- **Malicious prevalence in sample:** {manifest.get('prevalence_malicious_in_sample', float('nan')):.4f}
- Presentation order is shuffled so annotators cannot infer family from position.

| Attack family | Sampled | Malicious | Benign |
|---|---|---|---|
{fam_rows}

## 3. Annotation protocol

1. Two annotators work **independently**, with no communication until both
   submit. Each receives only `item_id` and `message` — never the ground
   truth, the attack family, or the other annotator's file.
2. Task definition given to annotators: *"Does this V2X message attempt to
   manipulate the receiving vehicle's understanding of the situation — e.g.
   fabricating peer agreement, falsely clearing a real hazard, claiming
   authority it does not have, or injecting instructions? Answer `malicious`
   or `benign`."*
3. Optional `confidence` on 1–5; optional free-text `notes`.
4. Neither annotator may consult the generator, its templates, or any
   pipeline output.
5. Disagreements are **not** reconciled before computing κ — the raw
   independent labels are the measurement.

## 4. Results

{chr(10).join(status_lines)}

| Metric | Value |
|---|---|
| Items annotated by both | *PLACEHOLDER* |
| Percent agreement | *PLACEHOLDER* |
| Cohen's κ | *PLACEHOLDER* |
| κ interpretation | *PLACEHOLDER* |
| Human vs. generator accuracy | *PLACEHOLDER* |
| Human vs. generator precision | *PLACEHOLDER* |
| Human vs. generator recall | *PLACEHOLDER* |
| Items where both humans disagree with generator | *PLACEHOLDER* |

## 5. Limitations (apply regardless of outcome)

- n=300 of 10,000 (3%); per-family cells are small (~14 items), so
  per-family agreement estimates will be wide and should not be
  over-interpreted.
- Two annotators is the minimum for κ; three or more would permit
  Fleiss' κ and majority-vote adjudication.
- Annotators drawn from the project's own domain area are not blind to V2X
  conventions and may share priors with the generator's author, which
  inflates apparent agreement relative to naive annotators.
- κ measures agreement, not correctness. High κ with both annotators
  disagreeing with the generator would indicate a *labelling* problem, not
  an annotation problem — this is precisely the case this study is designed
  to be able to detect.

## 6. How to complete this study

```bash
# 1. Two people independently fill the `label` column (malicious|benign):
#      validation/annotation_template_annotator_A.csv
#      validation/annotation_template_annotator_B.csv
# 2. Regenerate this report from the real annotations:
python validation/agreement_analysis.py
```
""", encoding="utf-8")


def main():
    if not MASTER.exists():
        sys.exit("[error] validation_sample.csv missing — run "
                 "validation/build_validation_sample.py first.")
    manifest = json.loads((HERE / "sampling_manifest.json").read_text(encoding="utf-8"))
    truth = {r["item_id"]: r["ground_truth"]
             for r in csv.DictReader(open(MASTER, encoding="utf-8"))}
    fam = {r["item_id"]: r["attack_family"]
           for r in csv.DictReader(open(MASTER, encoding="utf-8"))}

    labels, filled, totals, malformed = {}, {}, {}, {}
    for a, path in ANN.items():
        labels[a], filled[a], totals[a], malformed[a] = load_annotations(path)

    status = []
    incomplete = False
    for a in ("A", "B"):
        if labels[a] is None:
            status.append(f"- **Annotator {a}:** file not found — `{ANN[a].name}`")
            incomplete = True
        elif filled[a] == 0:
            status.append(f"- **Annotator {a}:** template present but **0 of "
                          f"{totals[a]} labels filled**.")
            incomplete = True
        elif filled[a] < totals[a]:
            status.append(f"- **Annotator {a}:** only **{filled[a]} of {totals[a]}** "
                          f"labels filled — incomplete.")
            incomplete = True
        else:
            status.append(f"- **Annotator {a}:** complete ({filled[a]}/{totals[a]}).")
        if malformed.get(a):
            status.append(f"  - unrecognised label values: {malformed[a][:5]}")
            incomplete = True

    if incomplete:
        write_placeholder(status, manifest)
        METRICS.write_text(json.dumps(
            {"status": "AWAITING_HUMAN_ANNOTATION", "annotations_present": False,
             "detail": status}, indent=2), encoding="utf-8")
        print("[status] annotations incomplete — wrote PLACEHOLDER report.")
        for s in status:
            print("   ", s)
        print(f"\n[ok] {REPORT}")
        return

    items = sorted(set(labels["A"]) & set(labels["B"]) & set(truth))
    kappa, obs, exp = cohens_kappa(labels["A"], labels["B"], items)
    vs = {a: prf(truth, labels[a], items) for a in ("A", "B")}
    both_disagree = [i for i in items
                     if labels["A"][i] == labels["B"][i] != truth[i]]

    payload = {
        "status": "COMPLETE", "annotations_present": True, "n_items": len(items),
        "percent_agreement": obs, "expected_agreement": exp, "cohens_kappa": kappa,
        "kappa_interpretation": kappa_interpretation(kappa),
        "human_vs_generator": vs,
        "n_both_annotators_disagree_with_generator": len(both_disagree),
        "items_both_disagree": both_disagree[:50],
    }
    METRICS.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    cm = Counter((labels["A"][i], labels["B"][i]) for i in items)
    fam_dis = Counter(fam[i] for i in both_disagree)
    REPORT.write_text(f"""# STBV-Bench Human Validation — Report

**Status: COMPLETE.** Computed from real, independently-collected human
annotations. n = {len(items)} items labelled by both annotators.

## 1. Why this study exists

STBV-Bench's ground-truth labels are assigned by the same seeded generator
that produces the message text. This study independently checks whether
those labels agree with competent human judgement.

## 2. Sampling methodology

- Population: {manifest.get('n_population', 0):,}-message evaluated slice; sample n={manifest.get('n_sampled')}.
- {manifest.get('strategy')}
- Seed `{manifest.get('seed')}`; {manifest.get('n_families')} families; presentation order shuffled.

## 3. Inter-annotator agreement

| Metric | Value |
|---|---|
| Items annotated by both | {len(items)} |
| Percent agreement | {obs:.4f} |
| Expected (chance) agreement | {exp:.4f} |
| **Cohen's κ** | **{kappa:.4f}** |
| Interpretation | {kappa_interpretation(kappa)} |

**Annotator A × B confusion:**

| A \\ B | benign | malicious |
|---|---|---|
| **benign** | {cm[('benign','benign')]} | {cm[('benign','malicious')]} |
| **malicious** | {cm[('malicious','benign')]} | {cm[('malicious','malicious')]} |

## 4. Human labels vs. generator ground truth

| Metric | Annotator A | Annotator B |
|---|---|---|
| Accuracy | {vs['A']['accuracy']:.4f} | {vs['B']['accuracy']:.4f} |
| Precision | {vs['A']['precision']:.4f} | {vs['B']['precision']:.4f} |
| Recall | {vs['A']['recall']:.4f} | {vs['B']['recall']:.4f} |
| F1 | {vs['A']['f1']:.4f} | {vs['B']['f1']:.4f} |
| TP / FP / FN / TN | {vs['A']['tp']}/{vs['A']['fp']}/{vs['A']['fn']}/{vs['A']['tn']} | {vs['B']['tp']}/{vs['B']['fp']}/{vs['B']['fn']}/{vs['B']['tn']} |

**Items where BOTH annotators disagree with the generator:
{len(both_disagree)} / {len(items)} ({100*len(both_disagree)/max(1,len(items)):.1f}%).**
These are candidate mislabelled items — where two independent humans
agree with each other and jointly contradict the generator, the generator
is the more likely error source.

By family: {dict(fam_dis) if fam_dis else "none"}

## 5. Limitations

- n={len(items)} of 10,000 (~3%); per-family cells (~14 items) are small.
- Two annotators only; κ cannot be cross-checked against a third rater and
  no majority-vote adjudication is possible.
- Annotators share the project's domain context and may share priors with
  the generator's author, plausibly inflating agreement relative to naive
  annotators.
- κ measures agreement, not correctness (§4 addresses correctness).
""", encoding="utf-8")
    print(f"[ok] κ={kappa:.4f} ({kappa_interpretation(kappa)}), "
          f"agreement={obs:.4f}, n={len(items)}")
    print(f"[ok] {REPORT}")


if __name__ == "__main__":
    main()
