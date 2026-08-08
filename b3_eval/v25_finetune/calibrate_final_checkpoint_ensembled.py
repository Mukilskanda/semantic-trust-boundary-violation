"""
b3_eval/v25_finetune/calibrate_final_checkpoint_ensembled.py
================================================================
HISTORICAL (closed investigation, kept for audit trail -- see
CALIBRATION_FIX_REPORT.md). Ran against the PRIOR final checkpoint
(semantic_gate_v3_mixed_lora_continued_merged, now superseded by
semantic_gate_v3_mixed_lora_hardmine_merged); the ensembled-fit
methodology this script tested was verified to improve ECE but degrade
deployed decision quality and was NOT adopted -- this finding is
checkpoint-policy-level (about the fixed 0.85 confidence floor), not
specific to the checkpoint this script happened to run against, and was
not re-run for the current checkpoint (not re-litigated; see
stbv_paper.tex Limitations item (vii)). Refits the final checkpoint's
calibration temperature using the SAME
inference procedure production actually uses: three-template ensembling
(DEFAULT + NARRATIVE + STRUCTURED, averaged), not the single-template
scoring calibrate_final_checkpoint.py used.

Root cause (PIPELINE_DIFFERENCE_REPORT.md): isce_config.yaml sets
enable_ensembling: true, so every real B3 call inside the pipeline
averages three independently-computed, temperature-scaled probabilities.
The deployed T=2.82 was fit on non-ensembled logits, a genuine
calibration-methodology mismatch. This script fixes that: for each
calibration-split sample, synthesizes all three template renderings via
the real synthesizer, scores each independently at T=1 (raw logits), then
fits T to minimize NLL on the ENSEMBLED (averaged) probability -- matching
exactly what deployment computes.

The calibration split's 85 samples are text+label pairs, not raw
structured messages; each is wrapped in a minimal synthetic CAM message
(same technique as run_v25b_full_ablation.py) so the real synthesizer can
render all three styles from it. This does not alter the calibration
samples' content or labels -- it only routes them through the actual
deployment rendering path instead of assuming a single fixed style.
"""
from __future__ import annotations
import json, math, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.synthesizer import synthesize_message, TemplateStyle  # noqa: E402
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402
import torch  # noqa: E402

MODEL_DIR = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3_mixed_lora_continued_merged"
CALIB_SPLIT = ROOT / "b3_eval" / "data" / "calibration_split.jsonl"
MAX_LENGTH = 256


def make_msg(text, i):
    return {
        "header": {"station_id": 40000 + i, "message_id": 1},
        "cam": {"generation_delta_time": 1000 + i,
                "cam_parameters": {"basic_container": {"station_type": 5,
                    "reference_position": {"latitude": 485512345, "longitude": 96123456}},
                    "high_frequency_container": {"basic_vehicle_container_high_frequency": {
                        "speed": 1200, "heading": 900, "yaw_rate": 0,
                        "steering_wheel_angle": 0, "lateral_acceleration": 0,
                        "longitudinal_acceleration": 0}}}},
        "certificate_id": f"CERT_5_{40000+i}", "cert_id": f"CERT_5_{40000+i}",
        "local_perception": {"camera": "CLEAR", "radar": "CLEAR", "lidar": "CLEAR"},
        "scene_context": {"peer_reports": [text], "rsu_messages": []},
    }


@torch.no_grad()
def get_logits(model, tok, texts, device, batch_size=32):
    model.eval()
    out = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i:i + batch_size]
        enc = tok(chunk, max_length=MAX_LENGTH, padding=True, truncation=True,
                   return_tensors="pt").to(device)
        out.extend(model(**enc).logits.float().cpu().tolist())
    return out


def softmax_p_malicious(logits, T):
    scaled = [v / T for v in logits]
    m = max(scaled)
    exps = [math.exp(v - m) for v in scaled]
    z = sum(exps)
    probs = [e / z for e in exps]
    return probs[1]  # index 1 = malicious, matching prob_malicious convention


def nll_ensembled(per_sample_logits_3, labels, T):
    """per_sample_logits_3: list of [logits_default, logits_narrative, logits_structured]."""
    total = 0.0
    for logits3, y in zip(per_sample_logits_3, labels):
        p_ens = sum(softmax_p_malicious(lg, T) for lg in logits3) / 3.0
        p_ens = min(max(p_ens, 1e-9), 1 - 1e-9)
        total -= math.log(p_ens) if y == 1 else math.log(1 - p_ens)
    return total / len(labels)


def ece_ensembled(per_sample_logits_3, labels, T, n_bins=15):
    confs, correct = [], []
    for logits3, y in zip(per_sample_logits_3, labels):
        p_ens = sum(softmax_p_malicious(lg, T) for lg in logits3) / 3.0
        pred = 1 if p_ens >= 0.5 else 0
        conf = p_ens if pred == 1 else 1 - p_ens
        confs.append(conf); correct.append(int(pred == y))
    bins = [[] for _ in range(n_bins)]
    for c, corr in zip(confs, correct):
        b = min(n_bins - 1, int(c * n_bins))
        bins[b].append((c, corr))
    n = len(confs)
    e = 0.0
    for b in bins:
        if not b:
            continue
        acc = sum(x[1] for x in b) / len(b)
        conf = sum(x[0] for x in b) / len(b)
        e += (len(b) / n) * abs(acc - conf)
    return e


def main():
    assert MODEL_DIR.exists(), f"final checkpoint missing: {MODEL_DIR}"
    device = "cuda" if torch.cuda.is_available() else "cpu"

    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR), local_files_only=True).to(device)

    rows = load = [json.loads(l) for l in CALIB_SPLIT.read_text(encoding="utf-8").splitlines() if l.strip()]
    labels = [int(r["label"]) for r in rows]

    print(f"[calib-ensembled] synthesizing 3 template styles for {len(rows)} calibration samples...")
    texts_by_style = {style: [] for style in TemplateStyle}
    for i, r in enumerate(rows):
        msg = make_msg(r["text"], i)
        for style in TemplateStyle:
            synt = synthesize_message([msg], {}, "urban", template=style)
            texts_by_style[style].append(synt["text"])

    print("[calib-ensembled] scoring each style (raw logits, T=1)...")
    logits_by_style = {}
    for style in TemplateStyle:
        logits_by_style[style] = get_logits(model, tok, texts_by_style[style], device)

    per_sample_logits_3 = []
    for i in range(len(rows)):
        per_sample_logits_3.append([logits_by_style[style][i] for style in TemplateStyle])

    print("[calib-ensembled] fitting temperature on ensembled probability...")
    best_T, best_nll = 1.0, nll_ensembled(per_sample_logits_3, labels, 1.0)
    for j in range(int((5.0 - 0.5) / 0.02) + 1):
        T = round(0.5 + 0.02 * j, 3)
        v = nll_ensembled(per_sample_logits_3, labels, T)
        if v < best_nll:
            best_nll, best_T = v, T

    ece_before = ece_ensembled(per_sample_logits_3, labels, 1.0)
    ece_after_old_T = ece_ensembled(per_sample_logits_3, labels, 2.82)
    ece_after_new_T = ece_ensembled(per_sample_logits_3, labels, best_T)

    result = {
        "model_dir": str(MODEL_DIR), "calibration_split": str(CALIB_SPLIT), "n": len(rows),
        "template_styles_used": [s.name for s in TemplateStyle],
        "old_temperature_single_template": 2.82,
        "new_temperature_ensembled": best_T,
        "nll_at_new_T": best_nll,
        "ece_uncalibrated_T1_ensembled": ece_before,
        "ece_old_T_applied_to_ensembled_scoring": ece_after_old_T,
        "ece_new_T_ensembled": ece_after_new_T,
        "note": "Fitted on the SAME 3-template-ensembled inference path production "
                "actually uses (isce_config.yaml enable_ensembling=true), closing the "
                "calibration-methodology mismatch identified in PIPELINE_DIFFERENCE_REPORT.md.",
    }
    out_path = HERE / "results" / "final_checkpoint_calibration_ensembled.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"\n[ok] {out_path}")


if __name__ == "__main__":
    main()
