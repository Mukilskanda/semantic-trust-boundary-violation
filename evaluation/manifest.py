"""
evaluation/manifest.py
=========================
Part 11 (Reproducibility): every experiment records a complete manifest --
configuration, seed(s), git commit, hardware, software versions, dataset
identity, timestamp -- written alongside its results so any number in the
paper can be traced to the exact run that produced it.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import platform
import subprocess
import sys
from typing import Any, Dict, Optional

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "NOT-A-GIT-CHECKOUT (record the artifact zip's hash instead)"


def _package_version(name: str) -> Optional[str]:
    try:
        mod = __import__(name)
        return getattr(mod, "__version__", "installed, no __version__")
    except Exception:
        return None


def _dataset_fingerprint(paths) -> Dict[str, str]:
    """Content hash of every dataset file used, so 'dataset version' is a
    verifiable fact, not a label."""
    out = {}
    for p in paths:
        p = pathlib.Path(p)
        if p.is_file():
            out[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        elif p.is_dir():
            h = hashlib.sha256()
            for f in sorted(p.rglob("*.json")):
                h.update(f.read_bytes())
            out[str(p.relative_to(ROOT)) + "/ (aggregate)"] = h.hexdigest()[:16]
    return out


def build_manifest(experiment_name: str, config: Dict[str, Any],
                   seeds, dataset_paths=()) -> Dict[str, Any]:
    return {
        "experiment": experiment_name,
        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "config": config,
        "seeds": list(seeds),
        "git_commit": _git_commit(),
        "hardware": {
            "machine": platform.machine(),
            "processor": platform.processor() or platform.machine(),
            "system": f"{platform.system()} {platform.release()}",
            "python_build": platform.python_build()[1],
            "note": "GPU details must be added manually when run on GPU hardware "
                    "(torch.cuda.get_device_name(0)); absent here if torch missing.",
        },
        "software": {
            "python": sys.version.split()[0],
            **{pkg: v for pkg in ("numpy", "scipy", "pandas", "matplotlib", "torch",
                                    "transformers", "cryptography", "yaml")
               if (v := _package_version(pkg)) is not None},
        },
        "dataset_fingerprints_sha256_16": _dataset_fingerprint(dataset_paths),
    }


def write_manifest(results_dir: pathlib.Path, manifest: Dict[str, Any]) -> pathlib.Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    path = results_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2))
    return path
