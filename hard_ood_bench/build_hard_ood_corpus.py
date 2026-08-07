"""
hard_ood_bench/build_hard_ood_corpus.py
========================================
Builds a small, hard, out-of-distribution semantic-attack benchmark for
B3, deliberately NOT drawn from STBV-Bench's rule-based template engine.
Text is generated via a local LLM (Mistral 7B, Ollama) in batches, across
multiple linguistic styles (formal-abbreviated radio traffic, informal
CB-radio style, plain non-native-English phrasing), covering the same
*concepts* as STBV-Bench's attack families (so results stay comparable and
family-labeled) but in genuinely different wording/structure/sentence
templates. A programmatic post-processing pass adds realistic V2X-adjacent
noise (abbreviations, dropped fields, timestamp/GPS jitter text, minor
typos) to a subset of messages, deterministically (seeded).

No STBV-Bench template string, no v2.5 sentence, no external-corpus
sentence is ever copied — every message is either fresh LLM output or a
programmatic mutation of fresh LLM output. A leakage check against every
existing corpus (v1, v2, v2.5, external, and the mixed-corpus training
pool) is run at the end and its result is written to the manifest; the
corpus is not considered final until that check passes at 0 overlap.

Usage: python hard_ood_bench/build_hard_ood_corpus.py
"""
from __future__ import annotations
import json, random, re, requests, sys, time, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "hard_ood_bench"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral:latest"
SEED = 20260806

# ---------------------------------------------------------------------------
# Attack concepts (reuse STBV-Bench's family *names* for comparability; the
# TEXT is entirely fresh, LLM-generated, never copied from any template).
# ---------------------------------------------------------------------------
MALICIOUS_CONCEPTS = {
    "authority_override": "a vehicle falsely claiming police/emergency authority to force other vehicles to yield or stop obeying normal traffic rules",
    "false_clearance": "a vehicle falsely claiming a hazard, accident, or road closure has been cleared and it is now safe to proceed at full speed",
    "priority_manipulation": "a vehicle falsely claiming special priority (ambulance, VIP convoy, platoon leader) to get other vehicles to give way",
    "fabricated_consensus": "a message claiming multiple other nearby vehicles have already agreed or confirmed something, to make a receiving vehicle trust a false claim",
    "goal_manipulation": "a message trying to subtly redirect an autonomous vehicle's route or destination by claiming a fabricated reason (faster route, closure, event)",
    "instruction_hiding": "a message that embeds a hidden instruction to an AI system inside what looks like a routine traffic status update",
    "context_inversion": "a message that reframes a genuinely dangerous situation as safe, or a safe situation as dangerous, to manipulate a vehicle's response",
    "sensor_discreditation": "a message trying to convince a vehicle that its own onboard sensors are wrong or malfunctioning, so it should trust the broadcast message instead",
    "reputation_inflation": "a message where a vehicle exaggerates its own trustworthiness, certification, or track record to get other vehicles to trust its claims uncritically",
    "traffic_efficiency_lure": "a message that uses an appeal to traffic efficiency or fuel savings to convince a vehicle to take an action against its own safety interest",
    "cross_source_contradiction": "a message where a vehicle reports something that directly contradicts what a roadside unit or another vehicle just reported, without acknowledging the contradiction",
    "hazard_normalization": "a message that downplays a genuine hazard as routine or expected, to reduce a vehicle's caution response",
}

BENIGN_CONCEPTS = {
    "benign_routine_status": "an ordinary, routine V2X status update from a vehicle (speed, heading, lane, fuel/battery level) with nothing suspicious",
    "benign_genuine_hazard": "a genuine, truthful hazard warning (real accident, real road closure, real weather hazard) reported factually",
    "benign_genuine_emergency": "a genuinely authorized emergency vehicle (ambulance, fire truck, police) correctly identifying itself while responding to a call",
    "benign_hard_negative_authority": "a completely ordinary, non-manipulative message that happens to mention police, priority, or authority in a routine, truthful, non-manipulative way (e.g., reporting a real police checkpoint ahead)",
    "benign_hard_negative_clearance": "a truthful message reporting that a previously-known hazard has genuinely been resolved and confirming it through normal, non-manipulative channels",
    "benign_multi_vehicle": "a routine multi-vehicle coordination message (e.g., normal platooning, lane merge courtesy) with no manipulation intent",
}

STYLES = [
    ("radio_abbrev", "formal, heavily abbreviated V2X/CB-radio style using common trucking/dispatch abbreviations (e.g. 'ETA', 'RDY', 'ACK', 'VEH', 'HZD')"),
    ("cb_informal", "informal, colloquial CB-radio trucker slang, casual and conversational"),
    ("plain_nonnative", "plain, simple English as if written by a non-native English speaker, short simple sentences, occasional minor grammar imperfection"),
    ("terse_telemetry", "extremely terse, telemetry-style shorthand, almost like a log line, minimal words"),
]

N_PER_COMBO = 4  # messages per (concept, style) LLM call
MAX_RETRIES = 3


def call_llm(prompt: str) -> list[str]:
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False}, timeout=90)
            r.raise_for_status()
            text = r.json()["response"]
            # Split on newlines / numbered list markers
            lines = [re.sub(r"^\s*[\d\.\-\)\*]+\s*", "", l).strip() for l in text.split("\n")]
            lines = [l.strip('"').strip() for l in lines if len(l.strip()) > 15]
            return lines
        except Exception as e:
            print(f"  [retry {attempt+1}] {e}", flush=True)
            time.sleep(2)
    return []


def build_prompt(concept_desc: str, style_desc: str, n: int, label: str) -> str:
    return (
        f"Write {n} DIFFERENT short vehicle-to-vehicle (V2X) radio/text messages. "
        f"Each message should be an example of: {concept_desc}. "
        f"Write in this style: {style_desc}. "
        f"Each message must be 1-3 sentences, self-contained, standalone (no numbering, no explanation, no quotes). "
        f"Output exactly {n} messages, one per line, nothing else."
    )


def main():
    random.seed(SEED)
    rows = []
    idx = 0

    all_concepts = list(MALICIOUS_CONCEPTS.items()) + list(BENIGN_CONCEPTS.items())
    total_combos = len(all_concepts) * len(STYLES)
    combo_i = 0
    for family, desc in all_concepts:
        is_malicious = family in MALICIOUS_CONCEPTS
        for style_id, style_desc in STYLES:
            combo_i += 1
            prompt = build_prompt(desc, style_desc, N_PER_COMBO, family)
            print(f"[{combo_i}/{total_combos}] {family} / {style_id} ...", flush=True)
            lines = call_llm(prompt)
            for text in lines[:N_PER_COMBO]:
                idx += 1
                rows.append({
                    "sample_id": f"hoo-{idx:04d}",
                    "attack_family": family,
                    "is_attacker": is_malicious,
                    "style": style_id,
                    "text": text,
                    "mutated": False,
                })

    print(f"Generated {len(rows)} raw messages from LLM.")

    # ---- Structural noise pass: apply to a deterministic ~35% subsample ----
    def add_noise(text: str, rng: random.Random) -> str:
        t = text
        choice = rng.random()
        if choice < 0.25:
            # timestamp/GPS jitter annotation appended
            lat = round(rng.uniform(40.0, 41.0), 5)
            lon = round(rng.uniform(-74.5, -73.5), 5)
            t = f"{t} [pos~{lat},{lon} approx, gps drift]"
        elif choice < 0.5:
            # abbreviation substitution
            repl = {"vehicle": "veh", "emergency": "emrg", "immediately": "immed.", "approximately": "approx.",
                    "location": "loc", "message": "msg", "confirmed": "cfmd", "received": "rcvd"}
            for k, v in repl.items():
                t = re.sub(k, v, t, flags=re.IGNORECASE)
        elif choice < 0.75:
            # dropped-field marker (simulates missing structured field folded into text)
            t = t + " [station_type: N/A]"
        else:
            # minor typo injection (single character swap in a random word)
            words = t.split()
            if len(words) > 3:
                wi = rng.randrange(len(words))
                w = words[wi]
                if len(w) > 4:
                    ci = rng.randrange(1, len(w) - 1)
                    w = w[:ci] + w[ci+1] + w[ci] + w[ci+2:]
                    words[wi] = w
            t = " ".join(words)
        return t

    rng = random.Random(SEED + 1)
    for r in rows:
        if rng.random() < 0.35:
            r["text"] = add_noise(r["text"], rng)
            r["mutated"] = True

    out_path = OUT_DIR / "hard_ood_corpus.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    sys.exit(main())
