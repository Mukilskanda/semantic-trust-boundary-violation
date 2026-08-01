#!/usr/bin/env python3
"""Computes ASR, average iterations, detection probability (overall,
per-family, per-strategy), failure-mode breakdown, and confidence-evolution
statistics from adaptive_attack_results.json. Read-only analysis."""
import json, pathlib
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
data = json.loads((HERE / "results" / "adaptive_attack_results.json").read_text())
results = data["results"]
n = len(results)

evaded = [r for r in results if r["outcome"] == "EVADED"]
detected_throughout = [r for r in results if r["outcome"] == "DETECTED_THROUGHOUT"]

asr = len(evaded) / n
avg_iters_all = sum(r["n_iterations"] for r in results) / n
avg_iters_success = sum(r["n_iterations"] for r in evaded) / len(evaded) if evaded else None

# detection probability at iteration 0 (baseline, before any mutation) is 1.0 by
# construction (all seeds are B3-correctly-detected malicious messages at t=0).
# Report detection probability AFTER k mutation rounds: fraction of seeds still
# detected at each iteration index across all seeds (right-padding finished
# trajectories with their final state).
max_it = data["manifest"]["max_iterations"]
detected_at_iter = []
confidence_at_iter = []  # mean confidence (of the predicted class) at iter k
p_malicious_at_iter = []
for k in range(max_it + 1):
    dets, confs, pms = [], [], []
    for r in results:
        trace = r["trace"]
        step = trace[k] if k < len(trace) else trace[-1]
        dets.append(1 if step["detected"] else 0)
        confs.append(step["confidence"])
        pms.append(step["p_malicious"])
    detected_at_iter.append(sum(dets) / len(dets))
    confidence_at_iter.append(sum(confs) / len(confs))
    p_malicious_at_iter.append(sum(pms) / len(pms))

# per-family ASR
by_family = defaultdict(list)
for r in results:
    by_family[r["family"]].append(r)
family_asr = {
    fam: {"n": len(rs), "asr": sum(1 for r in rs if r["outcome"] == "EVADED") / len(rs),
          "avg_iterations": sum(r["n_iterations"] for r in rs) / len(rs)}
    for fam, rs in sorted(by_family.items())
}

# per-strategy: how often each strategy was the WINNING (chosen) mutation
# across all rounds, and what fraction of the time using it led to the
# candidate becoming BENIGN in that same round (immediate-evasion credit)
strategy_chosen_count = defaultdict(int)
strategy_immediate_evasion = defaultdict(int)
for r in results:
    trace = r["trace"]
    for i in range(1, len(trace)):
        mut = trace[i]["mutation_applied"]
        if mut is None:
            continue
        strategy_chosen_count[mut] += 1
        if not trace[i]["detected"]:
            strategy_immediate_evasion[mut] += 1

strategy_stats = {
    s: {"times_chosen_as_best_candidate": strategy_chosen_count[s],
        "times_that_round_achieved_evasion": strategy_immediate_evasion[s],
        "evasion_rate_when_chosen": (strategy_immediate_evasion[s] / strategy_chosen_count[s])
                                     if strategy_chosen_count[s] else None}
    for s in data["manifest"]["mutation_strategies"]
}

# failure modes: characterize the seeds that never evaded within budget
failure_modes = []
for r in detected_throughout:
    trace = r["trace"]
    conf_start = trace[0]["confidence"]
    conf_end = trace[-1]["confidence"]
    failure_modes.append({
        "seed_id": r["seed_id"], "family": r["family"],
        "confidence_iter0": conf_start, "confidence_iter_final": conf_end,
        "confidence_delta": conf_end - conf_start,
        "mutations_tried": [t["mutation_applied"] for t in trace[1:] if t["mutation_applied"]],
    })

out = {
    "n_seeds": n,
    "attack_success_rate": asr,
    "n_evaded": len(evaded),
    "n_detected_throughout": len(detected_throughout),
    "average_iterations_all": avg_iters_all,
    "average_iterations_successful_only": avg_iters_success,
    "detection_probability_by_iteration": detected_at_iter,
    "mean_confidence_by_iteration": confidence_at_iter,
    "mean_p_malicious_by_iteration": p_malicious_at_iter,
    "family_breakdown": family_asr,
    "strategy_breakdown": strategy_stats,
    "failure_modes_detail": failure_modes,
}
out_path = HERE / "results" / "adaptive_attack_analysis.json"
out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "failure_modes_detail"}, indent=2))
print(f"\nWrote {out_path}")
