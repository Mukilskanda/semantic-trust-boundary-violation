import os
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

        # local_files_only=True: measured via tests/profile_b3_pipeline.py's H1
        # test to save ~12.3s per process by skipping HF Hub's online metadata
        # check, which is pointless here since the model path is always a
        # local checkpoint, never a Hub repo id.
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, local_files_only=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path, local_files_only=True)
        self.model.to(self.device).eval()

        self.id2label = getattr(self.model.config, "id2label", {0: "BENIGN", 1: "MALICIOUS"})

        # Load config to check if text_ensembling is enabled
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

    def _predict_probs(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
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
            
            flat_probs = self._predict_probs(flat_variants, batch_size)
            
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
            probs = self._predict_probs(texts, batch_size)
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

def get_predictor(model_path: str, max_length: int = 256, device: Optional[str] = None) -> SemanticGatePredictor:
    """Get or create cached SemanticGatePredictor instance for the given configuration."""
    resolved_path = resolve_model_path(model_path)
    cache_key = (resolved_path, max_length, str(device))
    if cache_key not in _PREDICTOR_CACHE:
        _PREDICTOR_CACHE[cache_key] = SemanticGatePredictor(resolved_path, max_length, device)
    return _PREDICTOR_CACHE[cache_key]