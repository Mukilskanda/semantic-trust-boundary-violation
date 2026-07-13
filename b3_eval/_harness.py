"""
b3_eval/_harness.py
=====================
Shared plumbing for the B3 evaluation harnesses. Loads the REAL predictor
when torch + a materialized checkpoint are present; otherwise returns an
honest "unavailable" marker so every harness degrades to skip-with-reason
rather than fabricating numbers.

None of the harnesses in this directory modify B3 or any other layer.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import platform
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MODEL_DIR = ROOT / "b3" / "solution_stb" / "b3_semantic_gate" / "model" / "semantic_gate_v3"


def checkpoint_status() -> Dict[str, Any]:
    """Distinguishes 'weights present' from 'LFS pointer stub' from
    'absent', so a harness can say exactly why it can't run."""
    binp = MODEL_DIR / "pytorch_model.bin"
    safep = MODEL_DIR / "model.safetensors"
    present = None
    for p in (safep, binp):
        if p.exists():
            present = p
            break
    if present is None:
        return {"ok": False, "reason": f"no weight file under {MODEL_DIR}"}
    size = present.stat().st_size
    if size < 10_000:  # LFS pointer stubs are ~130 bytes
        head = present.read_bytes()[:64]
        if b"git-lfs" in head:
            return {"ok": False, "reason": f"{present.name} is a {size}-byte Git LFS "
                    f"pointer, not weights -- run `git lfs pull`"}
        return {"ok": False, "reason": f"{present.name} is only {size} bytes -- likely truncated"}
    return {"ok": True, "path": str(present), "size_bytes": size,
            "sha256_16": hashlib.sha256(present.read_bytes()).hexdigest()[:16]}


def torch_status() -> Dict[str, Any]:
    try:
        import torch
        return {"ok": True, "version": torch.__version__,
                "cuda": torch.cuda.is_available(),
                "device_name": (torch.cuda.get_device_name(0)
                                if torch.cuda.is_available() else "cpu")}
    except Exception as e:
        return {"ok": False, "reason": f"torch import failed: {e}"}


def load_predictor(max_length: int = 256, device: Optional[str] = None):
    """Returns (predictor, None) on success or (None, reason) if the real
    model cannot be loaded. Never raises for the expected-absent cases."""
    ck = checkpoint_status()
    if not ck["ok"]:
        return None, ck["reason"]
    tt = torch_status()
    if not tt["ok"]:
        return None, tt["reason"]
    try:
        sys.path.insert(0, str(ROOT / "b3" / "solution_stb" / "b3_semantic_gate"))
        from inference import get_predictor
        pred = get_predictor(str(MODEL_DIR), max_length=max_length, device=device)
        return pred, None
    except Exception as e:
        return None, f"predictor load failed: {type(e).__name__}: {e}"


def predict_texts(predictor, texts: List[str], batch_size: int = 32) -> List[Dict[str, Any]]:
    """Uniform result dicts from the real predictor."""
    results = predictor.predict(texts, batch_size=batch_size)
    out = []
    for r in results:
        label = "MALICIOUS" if r.label == "MALICIOUS_SEMANTIC_MANIPULATION" else r.label
        out.append({"label": label, "label_id": r.label_id, "confidence": float(r.confidence)})
    return out


def env_manifest(experiment: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    m = {
        "experiment": experiment,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checkpoint": checkpoint_status(),
        "torch": torch_status(),
        "python": sys.version.split()[0],
        "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
    }
    if extra:
        m.update(extra)
    return m


def write_json(obj: Any, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2))
