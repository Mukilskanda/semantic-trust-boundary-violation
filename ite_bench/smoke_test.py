"""Quick sanity check: for each ITE-Bench attack family, confirm the
intended layer actually fires (non-trivial mass/score), before committing
to a full 10,000-sample run.

Correct protocol (matches how B1's replay/cert-rotation cache and MBD's
per-sender history both actually accumulate state -- confirmed by reading
orchestrator.py/scsv.py/mbd_layer.py directly): call pipeline.run([m])
ONCE PER MESSAGE in the window, sequentially, on a SINGLE persistent
pipeline instance, and score only the LAST call's result. A single
pipeline.run(full_window) call only ever processes messages[-1] through
B1, and only pre-populates MBD history for OTHER senders, not the
target's own prior messages -- confirmed by code inspection, not
assumed."""
import json, pathlib, sys, collections
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.orchestrator import ISCEPipeline
from b1_scsv.scsv import SCSV

rows = [json.loads(l) for l in (ROOT / "ite_bench" / "data" / "ite_bench.jsonl").read_text(encoding="utf-8").splitlines()]
by_family = collections.defaultdict(list)
for r in rows:
    by_family[r["attack_family"]].append(r)


def run_sequential(pipeline, messages):
    res = None
    for m in messages:
        res = pipeline.run([m], context="urban")
    return res


print(f"{'family':40s} {'layer':4s} {'decision':10s} {'b1_fatal':9s} {'mbd_evid':9s} {'b3_label':10s}")
for fam, samples in by_family.items():
    r = samples[0]
    pipeline = ISCEPipeline(scsv=SCSV(), enable_mbd=True, enable_cp=True, enable_b3=True)
    try:
        res = run_sequential(pipeline, r["messages"])
    except Exception as e:
        print(f"{fam:40s} ERROR: {e}")
        continue
    b1 = res.get("b1", {}) or {}
    mbd = res.get("mbd", {}) or {}
    b3 = res.get("b3", {}) or {}
    mbd_evidence = mbd.get("evidence") or []
    print(f"{fam:40s} {r['layer']:4s} {res.get('decision',''):10s} "
          f"{str(b1.get('fatal')):9s} "
          f"{str(len(mbd_evidence)):9s} {str(b3.get('label')):10s}  |  {mbd_evidence[:2]}")
