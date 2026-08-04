#!/usr/bin/env python3
"""
deployment_eval/aggregate_multirun.py
======================================
Aggregates every run produced by run_carla_multirun.py into 95%-CI
statistics and publication-quality plots.

Averages over ALL runs. There is no code path that selects, ranks, or
excludes a run on the basis of its result.

CI method: percentile bootstrap (10,000 resamples) over the per-run
values for run-level metrics, and over per-message values for latency
distributions. Fixed seed.
"""
from __future__ import annotations

import json
import pathlib
from collections import Counter, defaultdict

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
RUNS = HERE / "carla_multirun"
FIGS = RUNS / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

SEED = 42
N_BOOT = 10_000
rng = np.random.default_rng(SEED)


def ci(vals, n=N_BOOT):
    """Percentile bootstrap 95% CI of the mean."""
    v = np.asarray([x for x in vals if x is not None], dtype=float)
    if len(v) == 0:
        return (float("nan"),) * 3
    if len(v) == 1:
        return float(v[0]), float(v[0]), float(v[0])
    means = np.array([np.mean(rng.choice(v, len(v), replace=True)) for _ in range(n)])
    return float(v.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def fmt(m, lo, hi, p=2):
    return f"{m:.{p}f} [{lo:.{p}f}, {hi:.{p}f}]"


def main():
    files = sorted(RUNS.glob("run_*.json"))
    if not files:
        raise SystemExit("no runs found -- run run_carla_multirun.py first")
    runs = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    print(f"[agg] {len(runs)} runs: "
          f"{sorted(set(r['town'] for r in runs))} x "
          f"{sorted(set(r['seed'] for r in runs))}")

    # ---------------- run-level metrics ----------------
    run_metrics = {}
    for key, extract in [
        ("throughput_msg_s", lambda r: r["throughput_msg_s"]),
        ("cpu_percent", lambda r: r["cpu_percent"]),
        ("rss_mb", lambda r: r["rss_mb"]),
        ("peak_gpu_alloc_mb", lambda r: r["peak_gpu_alloc_mb"]),
        ("gpu_util_mean", lambda r: r.get("gpu", {}).get("gpu_util_mean")),
        ("gpu_mem_used_mean_mib", lambda r: r.get("gpu", {}).get("gpu_mem_used_mean_mib")),
    ]:
        m, lo, hi = ci([extract(r) for r in runs])
        run_metrics[key] = {"mean": m, "ci95_lo": lo, "ci95_hi": hi,
                            "per_run": [extract(r) for r in runs]}

    # ---------------- latency (pooled per-message) ----------------
    all_msgs = [m for r in runs for m in r["per_message"]]
    lat = np.array([m["total_ms"] for m in all_msgs], dtype=float)
    lat_stats = {
        "n_messages": int(len(lat)),
        "mean": float(lat.mean()),
        "p50": float(np.percentile(lat, 50)),
        "p95": float(np.percentile(lat, 95)),
        "p99": float(np.percentile(lat, 99)),
        "max": float(lat.max()),
    }
    m, lo, hi = ci([np.mean([x["total_ms"] for x in r["per_message"]]) for r in runs])
    lat_stats["mean_ci95"] = [lo, hi]
    # per-stage means, CI across runs
    stages = ["pki_ms", "b1_ms", "mbd_ms", "b2_ms", "cp_ms",
              "synthesizer_ms", "bridge_ms", "fusion_ms"]
    stage_stats = {}
    for s in stages:
        per_run = [np.mean([x[s] for x in r["per_message"] if x.get(s) is not None])
                   for r in runs]
        mm, l, h = ci(per_run)
        stage_stats[s] = {"mean": mm, "ci95_lo": l, "ci95_hi": h}

    # ---------------- per-scenario detection metrics ----------------
    scen_names = sorted(set(m["scenario"] for m in all_msgs))
    per_scenario = {}
    for sc in scen_names:
        rows_by_run = []
        for r in runs:
            msgs = [m for m in r["per_message"] if m["scenario"] == sc]
            if not msgs:
                continue
            # Ground truth is per MESSAGE, not per scenario: replay_attack's
            # first message is the genuine capture (benign) and only the
            # subsequent re-broadcasts are the attack. Classifying the whole
            # scenario by its first message would mislabel 39 of its 40
            # messages, so attack and benign messages are separated here.
            atk_m = [m for m in msgs if m["ground_truth"].startswith("attack")]
            ben_m = [m for m in msgs if not m["ground_truth"].startswith("attack")]

            def concern(ms):
                return sum(1 for m in ms if m["decision"] in ("CAUTION", "REJECT"))

            def rejects(ms):
                return sum(1 for m in ms if m["decision"] == "REJECT")

            rows_by_run.append({
                "n": len(msgs), "n_attack": len(atk_m), "n_benign": len(ben_m),
                # positive = system raised a concern (Caution or Reject),
                # matching the paper's own scoring convention
                "recall": concern(atk_m) / len(atk_m) if atk_m else None,
                "fnr": 1 - concern(atk_m) / len(atk_m) if atk_m else None,
                "reject_rate_attack": rejects(atk_m) / len(atk_m) if atk_m else None,
                "fpr": concern(ben_m) / len(ben_m) if ben_m else None,
                "reject_rate_benign": rejects(ben_m) / len(ben_m) if ben_m else None,
                "reject_rate": rejects(msgs) / len(msgs),
            })

        n_atk = sum(r["n_attack"] for r in rows_by_run)
        n_ben = sum(r["n_benign"] for r in rows_by_run)
        if n_atk and n_ben:
            gt = "mixed"
        elif n_atk:
            gt = "attack"
        else:
            gt = "benign"
        e = {"ground_truth": gt, "n_runs": len(rows_by_run),
             "n_messages_per_run": rows_by_run[0]["n"],
             "n_attack_messages_total": n_atk,
             "n_benign_messages_total": n_ben}
        for k in ["recall", "fnr", "reject_rate_attack",
                  "fpr", "reject_rate_benign", "reject_rate"]:
            vals = [r[k] for r in rows_by_run if r[k] is not None]
            if not vals:
                continue
            mm, l, h = ci(vals)
            e[k] = {"mean": mm, "ci95_lo": l, "ci95_hi": h}
        per_scenario[sc] = e

    # ---------------- decision distribution ----------------
    dec = Counter(m["decision"] for m in all_msgs)
    total = sum(dec.values())
    dec_dist = {}
    for d in ("ACCEPT", "CAUTION", "REJECT"):
        per_run = [Counter(m["decision"] for m in r["per_message"])[d] / len(r["per_message"])
                   for r in runs]
        mm, l, h = ci(per_run)
        dec_dist[d] = {"count": dec[d], "frac": dec[d] / total,
                       "mean": mm, "ci95_lo": l, "ci95_hi": h}

    # ---------------- B3 behaviour ----------------
    b3 = Counter(m.get("b3_label") for m in all_msgs)
    atk_msgs = [m for m in all_msgs if m["ground_truth"].startswith("attack")]
    b3_atk = Counter(m.get("b3_label") for m in atk_msgs)

    # ---------------- per-town ----------------
    per_town = {}
    for town in sorted(set(r["town"] for r in runs)):
        tr = [r for r in runs if r["town"] == town]
        tm = [m for r in tr for m in r["per_message"]]
        e = {"n_runs": len(tr), "n_messages": len(tm)}
        for k, vals in [("throughput_msg_s", [r["throughput_msg_s"] for r in tr]),
                        ("latency_mean_ms",
                         [np.mean([x["total_ms"] for x in r["per_message"]]) for r in tr]),
                        ("rss_mb", [r["rss_mb"] for r in tr]),
                        ("gpu_util_mean",
                         [r.get("gpu", {}).get("gpu_util_mean") for r in tr])]:
            mm, l, h = ci(vals)
            e[k] = {"mean": mm, "ci95_lo": l, "ci95_hi": h}
        per_town[town] = e

    payload = {
        "experiment": "carla_multirun_aggregate",
        "n_runs": len(runs),
        "towns": sorted(set(r["town"] for r in runs)),
        "seeds": sorted(set(r["seed"] for r in runs)),
        "total_messages": len(all_msgs),
        "ci_method": f"percentile bootstrap, {N_BOOT} resamples, seed {SEED}",
        "aggregation_policy": "mean over ALL runs; no run excluded or ranked",
        "run_level": run_metrics, "latency": lat_stats, "per_stage": stage_stats,
        "decision_distribution": dec_dist, "per_scenario": per_scenario,
        "per_town": per_town,
        "b3_labels_all": dict(b3), "b3_labels_attack_only": dict(b3_atk),
        "dropped_messages_total": sum(r["dropped_messages"] for r in runs),
        "offered_messages_total": sum(r["offered_messages"] for r in runs),
    }
    (RUNS / "aggregate.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # ---------------- CSV ----------------
    import csv
    with open(RUNS / "per_run_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["town", "seed", "n_messages", "wall_s", "throughput_msg_s",
                    "latency_mean_ms", "latency_p99_ms", "cpu_percent", "rss_mb",
                    "peak_gpu_alloc_mb", "gpu_util_mean", "accept", "caution", "reject"])
        for r in runs:
            L = np.array([m["total_ms"] for m in r["per_message"]])
            c = Counter(m["decision"] for m in r["per_message"])
            w.writerow([r["town"], r["seed"], r["n_messages"], round(r["wall_seconds"], 2),
                        round(r["throughput_msg_s"], 3), round(L.mean(), 2),
                        round(float(np.percentile(L, 99)), 2), round(r["cpu_percent"], 1),
                        round(r["rss_mb"], 1),
                        round(r["peak_gpu_alloc_mb"], 1) if r["peak_gpu_alloc_mb"] else "",
                        round(r.get("gpu", {}).get("gpu_util_mean", float("nan")), 1),
                        c["ACCEPT"], c["CAUTION"], c["REJECT"]])

    make_plots(runs, all_msgs, per_scenario, stage_stats)
    print_summary(payload)


def make_plots(runs, all_msgs, per_scenario, stage_stats):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 8, "axes.grid": True, "grid.alpha": 0.3})
    towns = sorted(set(r["town"] for r in runs))
    tcol = dict(zip(towns, ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]))

    # 1 -- latency distribution per town (boxplot) + pooled histogram
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.7))
    data = [[m["total_ms"] for r in runs if r["town"] == t for m in r["per_message"]]
            for t in towns]
    bp = a1.boxplot(data, tick_labels=towns, showfliers=False, patch_artist=True,
                    medianprops=dict(color="black"))
    for p, t in zip(bp["boxes"], towns):
        p.set_facecolor(tcol[t]); p.set_alpha(0.75)
    a1.axhline(100, color="#C44E52", ls="--", lw=1, label="100 ms CAM budget")
    a1.set_ylabel("End-to-end latency (ms)")
    a1.set_title("Latency by town (all seeds pooled)", fontsize=8)
    a1.legend(fontsize=6)
    allv = [m["total_ms"] for m in all_msgs]
    a2.hist(allv, bins=60, color="#4C72B0", alpha=0.85)
    a2.axvline(np.percentile(allv, 99), color="k", ls=":", lw=1,
               label=f"p99={np.percentile(allv,99):.0f} ms")
    a2.axvline(100, color="#C44E52", ls="--", lw=1, label="100 ms budget")
    a2.set_xlabel("Latency (ms)"); a2.set_ylabel("messages")
    a2.set_title(f"Pooled latency ({len(allv):,} messages)", fontsize=8)
    a2.legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(FIGS / "multirun_latency.pdf"); fig.savefig(FIGS / "multirun_latency.png", dpi=150)
    plt.close(fig)

    # 2 -- throughput / RSS / GPU util per town, error bars over seeds
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.4))
    for ax, key, lab in [(axes[0], "throughput_msg_s", "Throughput (msg/s)"),
                         (axes[1], "rss_mb", "Process RSS (MB)"),
                         (axes[2], "gpu", "GPU utilization (%)")]:
        means, errs = [], []
        for t in towns:
            vals = [(r.get("gpu", {}).get("gpu_util_mean") if key == "gpu" else r[key])
                    for r in runs if r["town"] == t]
            vals = [v for v in vals if v is not None]
            means.append(np.mean(vals))
            errs.append(1.96 * np.std(vals, ddof=1) / np.sqrt(len(vals)) if len(vals) > 1 else 0)
        ax.bar(towns, means, yerr=errs, capsize=4,
               color=[tcol[t] for t in towns], alpha=0.85)
        ax.set_ylabel(lab, fontsize=7)
        ax.tick_params(labelsize=7)
    fig.suptitle("Per-town resource use (mean ± 95% CI over 5 seeds)", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGS / "multirun_resources.pdf"); fig.savefig(FIGS / "multirun_resources.png", dpi=150)
    plt.close(fig)

    # 3 -- per-scenario detection with CI
    fig, ax = plt.subplots(figsize=(7.0, 2.9))
    names = list(per_scenario)
    xs = np.arange(len(names))
    vals, los, his, cols = [], [], [], []
    for n in names:
        e = per_scenario[n]
        k = "fpr" if e["ground_truth"] == "benign" else "recall"
        if k not in e:
            k = "recall" if "recall" in e else "fpr"
        vals.append(e[k]["mean"])
        los.append(e[k]["mean"] - e[k]["ci95_lo"])
        his.append(e[k]["ci95_hi"] - e[k]["mean"])
        cols.append("#4C72B0" if e["ground_truth"] == "benign" else "#C44E52")
    ax.bar(xs, vals, yerr=[los, his], capsize=3, color=cols, alpha=0.85)
    ax.set_xticks(xs)
    ax.set_xticklabels(names, rotation=38, ha="right", fontsize=6.5)
    ax.set_ylabel("Recall (attack) / FPR (benign)")
    ax.set_ylim(0, 1.05)
    ax.set_title("Per-scenario detection over 15 runs (mean ± 95% CI). "
                 "Red = attack (recall, higher better); blue = benign (FPR, lower better)",
                 fontsize=7.5)
    fig.tight_layout()
    fig.savefig(FIGS / "multirun_per_scenario.pdf")
    fig.savefig(FIGS / "multirun_per_scenario.png", dpi=150)
    plt.close(fig)

    # 4 -- per-stage latency with CI (log)
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    labs = ["PKI", "B1", "MBD", "B2", "CP", "Synth", "B3", "Fusion"]
    keys = ["pki_ms", "b1_ms", "mbd_ms", "b2_ms", "cp_ms",
            "synthesizer_ms", "bridge_ms", "fusion_ms"]
    m = [stage_stats[k]["mean"] for k in keys]
    lo = [stage_stats[k]["mean"] - stage_stats[k]["ci95_lo"] for k in keys]
    hi = [stage_stats[k]["ci95_hi"] - stage_stats[k]["mean"] for k in keys]
    ax.bar(labs, m, yerr=[lo, hi], capsize=3,
           color=["#4C72B0"] * 6 + ["#C44E52"] + ["#4C72B0"], alpha=0.9)
    ax.set_yscale("log"); ax.set_ylabel("Mean latency (ms, log)")
    ax.set_title("Per-stage latency, 15 runs (±95% CI)", fontsize=8)
    ax.tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig(FIGS / "multirun_stages.pdf"); fig.savefig(FIGS / "multirun_stages.png", dpi=150)
    plt.close(fig)
    print(f"[figs] 4 vector figures -> {FIGS}")


def print_summary(p):
    print(f"\n{'='*64}\nAGGREGATE over {p['n_runs']} runs "
          f"({len(p['towns'])} towns x {len(p['seeds'])} seeds), "
          f"{p['total_messages']:,} messages\n{'='*64}")
    r = p["run_level"]
    print(f"Throughput  : {fmt(r['throughput_msg_s']['mean'], r['throughput_msg_s']['ci95_lo'], r['throughput_msg_s']['ci95_hi'])} msg/s")
    print(f"Latency mean: {p['latency']['mean']:.2f} ms  "
          f"[{p['latency']['mean_ci95'][0]:.2f}, {p['latency']['mean_ci95'][1]:.2f}]")
    print(f"  p50/p95/p99: {p['latency']['p50']:.1f} / {p['latency']['p95']:.1f} / {p['latency']['p99']:.1f} ms")
    print(f"RSS         : {fmt(r['rss_mb']['mean'], r['rss_mb']['ci95_lo'], r['rss_mb']['ci95_hi'], 1)} MB")
    print(f"GPU util    : {fmt(r['gpu_util_mean']['mean'], r['gpu_util_mean']['ci95_lo'], r['gpu_util_mean']['ci95_hi'], 1)} %")
    print(f"Peak GPU alloc: {fmt(r['peak_gpu_alloc_mb']['mean'], r['peak_gpu_alloc_mb']['ci95_lo'], r['peak_gpu_alloc_mb']['ci95_hi'], 1)} MB")
    print(f"Dropped msgs: {p['dropped_messages_total']} / {p['offered_messages_total']} offered")
    print(f"\nB3 labels (attack messages only): {p['b3_labels_attack_only']}")
    print("\nPer-scenario (mean [95% CI]):")
    for sc, e in p["per_scenario"].items():
        parts = []
        if "recall" in e:
            parts.append(f"recall={fmt(e['recall']['mean'], e['recall']['ci95_lo'], e['recall']['ci95_hi'], 3)}")
        if "fpr" in e:
            parts.append(f"FPR={fmt(e['fpr']['mean'], e['fpr']['ci95_lo'], e['fpr']['ci95_hi'], 3)}")
        print(f"  {sc:24s} {e['ground_truth']:6s} " + "  ".join(parts))


if __name__ == "__main__":
    main()
