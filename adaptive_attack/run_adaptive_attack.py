#!/usr/bin/env python3
"""
run_adaptive_attack.py
========================
A real, iterative adaptive-attacker evaluation against the FROZEN,
unmodified B3 checkpoint. No retraining, no fine-tuning -- inference only.

Loop, per seed attack:
    generate attack (seed) -> evaluate -> observe prediction/confidence
    -> if predicted MALICIOUS (still detected): produce 9 candidate
       mutations (one per required strategy) from the CURRENT text,
       evaluate all 9, keep the candidate with the lowest P(malicious)
       as the new "current text" for the next round
    -> if predicted BENIGN: STOP -- evasion achieved (attack succeeds)
    -> if max_iterations reached while still MALICIOUS: STOP -- attack
       fails (B3 never evaded for this seed)

Methodology note (interpretation disclosed, not silently assumed): the
task specification's stop condition "until detected or max iterations"
is interpreted here as the natural adversarial-evasion framing --
"detected" ends a round unsuccessfully only in the sense that mutation
continues *while* detected, and the run truly stops the moment detection
is evaded (success) or the iteration budget is exhausted while detection
persists (failure). This is stated explicitly in
ADAPTIVE_ATTACK_EVALUATION.md's methodology section.

Seeds are drawn from external_semantic_eval's already-evaluated corpus:
every malicious message B3 currently detects correctly (true=MALICIOUS,
pred=MALICIOUS), stratified across all 9 non-benign attack families.
"""
from __future__ import annotations
import json, pathlib, random, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "b3" / "solution_stb" / "b3_semantic_gate"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from mutations import MUTATIONS

HERE = pathlib.Path(__file__).resolve().parent
MAX_ITERATIONS = 10
SEEDS_PER_FAMILY = 6
MASTER_SEED = 20260802


def checkpoint_status():
    model_dir = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3"
    binp = model_dir / "pytorch_model.bin"
    if not binp.exists():
        return {"ok": False, "reason": f"no weight file under {model_dir}"}, model_dir
    size = binp.stat().st_size
    if size < 10_000:
        return {"ok": False, "reason": f"{binp.name} is a {size}-byte LFS pointer"}, model_dir
    import hashlib
    return {"ok": True, "size_bytes": size,
            "sha256_16": hashlib.sha256(binp.read_bytes()).hexdigest()[:16]}, model_dir


def load_seeds():
    corpus = json.loads((ROOT / "external_semantic_eval" / "external_corpus.json").read_text())
    results = json.loads((ROOT / "external_semantic_eval" / "external_eval_results.json").read_text())
    text_by_id = {e["id"]: e["text"] for e in corpus["entries"]}
    by_family = {}
    for m in results["per_message"]:
        if m["true_label"] == "MALICIOUS" and m["pred_label"] == "MALICIOUS" and m["family"] != "benign_control":
            by_family.setdefault(m["family"], []).append(m["id"])
    rng = random.Random(MASTER_SEED)
    seeds = []
    for fam, ids in sorted(by_family.items()):
        ids = ids[:]
        rng.shuffle(ids)
        for i in ids[:SEEDS_PER_FAMILY]:
            seeds.append({"seed_id": i, "family": fam, "text": text_by_id[i]})
    return seeds


def p_malicious(result):
    return float(result.confidence) if result.label_id == 1 else 1.0 - float(result.confidence)


def run_one_seed(predictor, seed_entry, rng):
    trace = []
    current_text = seed_entry["text"]
    strategy_names = list(MUTATIONS.keys())

    for it in range(MAX_ITERATIONS + 1):
        r = predictor.predict([current_text], batch_size=1)[0]
        pm = p_malicious(r)
        detected = (r.label_id == 1)
        trace.append({
            "iteration": it, "text": current_text, "detected": detected,
            "label": r.label, "confidence": float(r.confidence), "p_malicious": pm,
            "mutation_applied": trace[-1]["_next_mutation"] if trace else None,
        })
        if not detected:
            return {"seed_id": seed_entry["seed_id"], "family": seed_entry["family"],
                    "outcome": "EVADED", "n_iterations": it, "trace": _strip(trace)}
        if it == MAX_ITERATIONS:
            return {"seed_id": seed_entry["seed_id"], "family": seed_entry["family"],
                    "outcome": "DETECTED_THROUGHOUT", "n_iterations": it, "trace": _strip(trace)}

        # generate all 9 candidates from current text, pick lowest p_malicious
        candidates = []
        for name in strategy_names:
            try:
                cand_text = MUTATIONS[name](current_text, rng)
            except Exception:
                cand_text = current_text
            if not cand_text or not cand_text.strip():
                cand_text = current_text
            candidates.append((name, cand_text))

        cand_texts = [c[1] for _, c in enumerate(candidates)]
        # dedupe identical candidates for fewer redundant model calls, keep mapping
        unique_texts = list(dict.fromkeys(cand_texts))
        preds = predictor.predict(unique_texts, batch_size=len(unique_texts))
        pm_by_text = {t: p_malicious(p) for t, p in zip(unique_texts, preds)}

        best_name, best_text, best_pm = None, None, 2.0
        for name, ctext in candidates:
            pm_c = pm_by_text[ctext]
            if pm_c < best_pm:
                best_name, best_text, best_pm = name, ctext, pm_c

        trace[-1]["_next_mutation"] = best_name
        current_text = best_text

    # unreachable
    return {"seed_id": seed_entry["seed_id"], "family": seed_entry["family"],
            "outcome": "DETECTED_THROUGHOUT", "n_iterations": MAX_ITERATIONS, "trace": _strip(trace)}


def _strip(trace):
    return [{k: v for k, v in t.items() if not k.startswith("_")} for t in trace]


def main():
    ck, model_dir = checkpoint_status()
    if not ck["ok"]:
        print(f"[SKIP] checkpoint unavailable: {ck['reason']}")
        return 0
    try:
        from inference import get_predictor
    except Exception as e:
        print(f"[SKIP] predictor import failed: {e}")
        return 0

    predictor = get_predictor(str(model_dir), max_length=256)
    seeds = load_seeds()
    print(f"Loaded {len(seeds)} seeds across {len(set(s['family'] for s in seeds))} families")

    rng = random.Random(MASTER_SEED + 1)
    all_results = []
    for i, seed_entry in enumerate(seeds):
        res = run_one_seed(predictor, seed_entry, rng)
        all_results.append(res)
        print(f"[{i+1}/{len(seeds)}] {seed_entry['seed_id']} ({seed_entry['family']}): "
              f"{res['outcome']} after {res['n_iterations']} iteration(s)")

    out = {
        "manifest": {
            "experiment": "adaptive_attack_evaluation",
            "checkpoint": ck,
            "max_iterations": MAX_ITERATIONS,
            "seeds_per_family": SEEDS_PER_FAMILY,
            "master_seed": MASTER_SEED,
            "mutation_strategies": list(MUTATIONS.keys()),
            "n_seeds": len(seeds),
            "note": "Frozen B3 checkpoint; no retraining or fine-tuning. Inference only.",
        },
        "results": all_results,
    }
    out_path = HERE / "results" / "adaptive_attack_results.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
