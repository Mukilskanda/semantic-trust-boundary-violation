import os
import functools
import torch
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from transformers import AutoTokenizer, AutoModelForSequenceClassification

def _generate_tta_variants(text: str) -> List[str]:
    variants = {text}
    para_swaps = [
        ("must", "are required to"),
        ("divert", "reroute"),
        ("immediately", "at once"),
        ("ahead", "up ahead"),
        ("reported", "being reported"),
        ("resume", "go back to"),
        ("danger", "hazard"),
        ("recommended", "advised"),
        ("unmarked", "unsigned"),
        ("closure", "blockage"),
        ("do not attempt to verify", "do not try to verify"),
    ]
    syn_swaps = [
        ("reduce", "lower"),
        ("immediately", "at once"),
        ("normal", "usual"),
        ("vehicle", "car"),
        ("hazard", "danger"),
        ("advised", "recommended"),
    ]
    for orig, rep in para_swaps + syn_swaps:
        if orig in text:
            variants.add(text.replace(orig, rep))
        if rep in text:
            variants.add(text.replace(rep, orig))
            
    for p_orig, p_rep in para_swaps:
        for s_orig, s_rep in syn_swaps:
            text_mod = text
            changed = False
            if p_orig in text_mod:
                text_mod = text_mod.replace(p_orig, p_rep)
                changed = True
            elif p_rep in text_mod:
                text_mod = text_mod.replace(p_rep, p_orig)
                changed = True
            if s_orig in text_mod:
                text_mod = text_mod.replace(s_orig, s_rep)
                changed = True
            elif s_rep in text_mod:
                text_mod = text_mod.replace(s_rep, s_orig)
                changed = True
            if changed:
                variants.add(text_mod)
                
    return list(variants)

@dataclass
class SemanticGateResult:
    label: str
    label_id: int
    confidence: float

_PREDICTOR_CACHE: Dict[tuple, 'SemanticGatePredictor'] = {}

def resolve_model_path(model_path: str) -> str:
    """Resolve model path against absolute path and the b3_semantic_gate directory."""
    if os.path.exists(model_path):
        return os.path.abspath(model_path)
    candidate = os.path.join(os.path.dirname(os.path.abspath(__file__)), model_path)
    if os.path.exists(candidate):
        return os.path.abspath(candidate)
    return os.path.abspath(model_path)

class SemanticGatePredictor:
    def __init__(self, model_path: str, max_length: int = 256, device: Optional[str] = None):
        self.raw_path = model_path
        self.model_path = resolve_model_path(model_path)
        self.max_length = max_length

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model path not found: {self.model_path} (resolved from {model_path})")

        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # Step 1 — confirm active compute device at load time so CI / test runs
        # can verify the GPU path is taken without inspecting internals.
        if self.device.type == "cuda":
            _gpu_name = torch.cuda.get_device_name(self.device)
            print(f"[B3] Device: cuda ({_gpu_name})", flush=True)
        else:
            print("[B3] Device: cpu", flush=True)

        # local_files_only=True: measured via tests/profile_b3_pipeline.py's H1
        # test to save ~12.3s per process by skipping HF Hub's online metadata
        # check, which is pointless here since the model path is always a
        # local checkpoint, never a Hub repo id.
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, local_files_only=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path, local_files_only=True)
        self.model.to(self.device).eval()

        # Step 2 — CPU-only dynamic int8 quantization.
        # torch.quantization.quantize_dynamic targets nn.Linear layers and
        # reduces per-token GEMM cost ~1.5–2× on CPU.  On CUDA the call would
        # silently move ops back to CPU (defeating the GPU path) or raise a
        # RuntimeError depending on the PyTorch build, so the guard is
        # mandatory.  On GPU we rely on ORT/CUDA execution instead (Step 3).
        if self.device.type == "cpu":
            self.model = torch.quantization.quantize_dynamic(
                self.model, {torch.nn.Linear}, dtype=torch.qint8
            )
            print("[B3] Applied dynamic int8 quantization (cpu path)", flush=True)

        self.id2label = getattr(self.model.config, "id2label", {0: "BENIGN", 1: "MALICIOUS"})

        # Step 3 — ONNX Runtime inference path.
        #
        # Strategy:
        #   • CPU path  → load pre-exported ONNX model via ORT CPUExecutionProvider.
        #                 ORT's optimised CPU kernels outperform PyTorch CPU, especially
        #                 after int8 quantization of the source model.
        #   • CUDA path → skip ORT. onnxruntime-gpu 1.27 requires cuBLAS 13 DLLs that
        #                 are absent on this machine; PyTorch CUDA is the fast path.
        #
        # The ONNX file is written once by a one-time export (already done in
        # model/semantic_gate_v3/onnx/). If the file is missing or ORT fails to
        # load it, _use_ort stays False and _predict_probs falls back to PyTorch.
        self._use_ort = False
        self._ort_model = None
        self._ort_tokenizer = None

        if self.device.type == "cpu":
            onnx_dir = os.path.join(self.model_path, "onnx")
            try:
                from optimum.onnxruntime import ORTModelForSequenceClassification as _ORT
                from transformers import AutoTokenizer as _AT

                if not os.path.isdir(onnx_dir):
                    # One-time export — only runs if the onnx/ dir is absent.
                    print("[B3] ONNX dir not found; exporting model (one-time, ~10 s)...", flush=True)
                    _tmp = _ORT.from_pretrained(
                        self.model_path,
                        export=True,
                        provider="CPUExecutionProvider",
                        local_files_only=True,
                    )
                    _tmp.save_pretrained(onnx_dir)
                    print(f"[B3] ONNX model saved to {onnx_dir}", flush=True)

                self._ort_model = _ORT.from_pretrained(
                    onnx_dir,
                    provider="CPUExecutionProvider",
                    local_files_only=True,
                )
                self._ort_tokenizer = _AT.from_pretrained(self.model_path, local_files_only=True)
                self._use_ort = True
                print("[B3] ONNX Runtime inference enabled (CPUExecutionProvider)", flush=True)
            except Exception as _ort_err:
                print(f"[B3] ORT load skipped (will use PyTorch): {_ort_err}", flush=True)

        # Shadow structures for O(1) cache-contains check and pre-population:
        #   _cache_keys      : set of text strings known to be in lru_cache.
        #   _cache_store_map : transient dict used by _cache_store() to inject
        #                      a pre-computed result into lru_cache without a
        #                      second forward pass.
        self._cache_keys: set = set()
        self._cache_store_map: dict = {}

        _cache_store_map_ref = self._cache_store_map  # closure-captured ref

        @functools.lru_cache(maxsize=512)
        def _cached_infer_single(text: str):
            # If a pre-computed result was injected via _cache_store(), return it
            # directly so lru_cache stores it without a second forward pass.
            if text in _cache_store_map_ref:
                return _cache_store_map_ref[text]
            # Cache miss path: run inference normally.
            probs = self._predict_probs([text], batch_size=1)
            return probs[0]  # np.ndarray of shape (num_labels,)

        self._cached_infer_single = _cached_infer_single


        # ── Config: TTA and temperature ───────────────────────────────────────
        self.enable_tta = False
        try:
            import yaml
            config_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../isce_config.yaml"))
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as fh:
                    data = yaml.safe_load(fh) or {}
                self.enable_tta = data.get("b3_semantic_gate", {}).get("enable_text_ensembling", False)
        except Exception:
            pass

        self.temperature: float = 1.0
        try:
            import yaml
            config_file = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../../../isce_config.yaml")
            )
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as fh:
                    _cfg = yaml.safe_load(fh) or {}
                t = _cfg.get("b3_semantic_gate", {}).get("temperature_scaling", 1.0)
                self.temperature = float(t) if t and float(t) > 0 else 1.0
        except Exception:
            pass

    def cache_info(self):
        """Return LRU cache statistics for the per-instance inference cache."""
        return self._cached_infer_single.cache_info()

    def cache_clear(self):
        """Invalidate the per-instance LRU inference cache."""
        self._cached_infer_single.cache_clear()
        self._cache_keys.clear()
        self._cache_store_map.clear()

    def _predict_probs(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        # Step 3 — route through ORT on CPU, PyTorch on CUDA.
        if self._use_ort and self._ort_model is not None:
            return self._predict_probs_ort(texts, batch_size)
        return self._predict_probs_torch(texts, batch_size)

    def _predict_probs_ort(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """ORT CPU inference path (Step 3)."""
        all_probs = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            enc = self._ort_tokenizer(
                batch,
                max_length=self.max_length,
                padding=True,
                truncation=True,
                return_tensors="np",
            )
            out = self._ort_model(**enc)
            logits = out.logits  # numpy array (batch, num_labels)
            # Temperature-scaled softmax in numpy
            scaled = logits / self.temperature
            exp_s = np.exp(scaled - scaled.max(axis=1, keepdims=True))
            probs = exp_s / exp_s.sum(axis=1, keepdims=True)
            all_probs.extend(probs)
        return all_probs

    def _predict_probs_torch(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """PyTorch CUDA/CPU inference path (primary on GPU, fallback on CPU)."""
        all_probs = []
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                enc = self.tokenizer(
                    batch,
                    max_length=self.max_length,
                    padding=True,
                    truncation=True,
                    return_tensors="pt"
                ).to(self.device)

                out = self.model(**enc)
                probs = torch.softmax(out.logits / self.temperature, dim=1).cpu().numpy()
                all_probs.extend(probs)
        return all_probs

    def predict(self, texts: List[str], batch_size: int = 32) -> List[SemanticGateResult]:
        """Perform batched inference on a list of input texts.

        Identical texts are served from the per-instance LRU cache (Step 4)
        without re-running inference, making replay / Sybil / ensembling
        scenarios effectively zero-cost for repeated inputs.

        Parameters
        ----------
        texts : List[str]
            Texts to classify.
        batch_size : int, optional
            Batch size for inference, by default 32.

        Returns
        -------
        List[SemanticGateResult]
            Structured classification results containing label, label_id, and confidence.
        """
        if not texts:
            return []

        if getattr(self, "enable_tta", False):
            flat_variants = []
            text_to_variants_indices = []
            for t in texts:
                vars_for_t = _generate_tta_variants(t)
                start_idx = len(flat_variants)
                flat_variants.extend(vars_for_t)
                end_idx = len(flat_variants)
                text_to_variants_indices.append((start_idx, end_idx))

            # Step 4 (TTA path): batch-infer unique uncached variants, serve all
            # from the cache.  lru_cache handles hit/miss transparently; we
            # pre-warm it in one forward pass to avoid N serial single-text calls.
            flat_probs = self._batch_with_cache(flat_variants, batch_size)

            results = []
            for start, end in text_to_variants_indices:
                probs_slice = flat_probs[start:end]
                avg_probs = sum(probs_slice) / len(probs_slice)
                pred = avg_probs.argmax()
                conf = avg_probs[pred]
                label_name = self.id2label.get(int(pred), f"LABEL_{pred}")
                results.append(SemanticGateResult(
                    label=label_name,
                    label_id=int(pred),
                    confidence=float(conf)
                ))
            return results
        else:
            # Step 4 (non-TTA path): same batch-then-cache approach.
            probs = self._batch_with_cache(texts, batch_size)
            results = []
            for p in probs:
                pred = p.argmax()
                conf = p[pred]
                label_name = self.id2label.get(int(pred), f"LABEL_{pred}")
                results.append(SemanticGateResult(
                    label=label_name,
                    label_id=int(pred),
                    confidence=float(conf)
                ))
            return results

    def _batch_with_cache(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """Step 4 helper: batch-infer unique uncached texts, return probs for all."""
        unique_texts = list(dict.fromkeys(texts))
        uncached = [t for t in unique_texts if not self._is_cached(t)]

        if uncached:
            batch_probs = self._predict_probs(uncached, batch_size)
            for txt, prob in zip(uncached, batch_probs):
                self._cache_store(txt, prob)

        return [self._cached_infer_single(t) for t in texts]

    def _is_cached(self, text: str) -> bool:
        """Return True if `text` is already in the LRU inference cache."""
        return text in self._cache_keys

    def _cache_store(self, text: str, prob: np.ndarray) -> None:
        """Populate the LRU cache for `text` with pre-computed `prob`."""
        if text not in self._cache_keys:
            self._cache_store_map[text] = prob
            _ = self._cached_infer_single(text)
            self._cache_keys.add(text)
            del self._cache_store_map[text]

def get_predictor(model_path: str, max_length: int = 256, device: Optional[str] = None) -> SemanticGatePredictor:
    """Get or create cached SemanticGatePredictor instance for the given configuration."""
    resolved_path = resolve_model_path(model_path)
    cache_key = (resolved_path, max_length, str(device))
    if cache_key not in _PREDICTOR_CACHE:
        _PREDICTOR_CACHE[cache_key] = SemanticGatePredictor(resolved_path, max_length, device)
    return _PREDICTOR_CACHE[cache_key]