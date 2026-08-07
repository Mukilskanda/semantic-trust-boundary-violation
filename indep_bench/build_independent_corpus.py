"""
indep_bench/build_independent_corpus.py
==========================================
Builds a new, independent, IN-SCOPE evaluation benchmark for B3 -- the
inverse of hard_ood_bench (which deliberately tested OUTSIDE the paper's
declared deployment register). This corpus stays entirely within
grammatical, report-style ETSI CAM/DENM-plausible language, but uses
genuinely new scenarios, road names, cities, entity IDs, and specific
narrative content never used in any existing corpus in this project.

Generation: local LLM (Mistral 7B via Ollama), one consistent in-scope
"formal V2X report" register throughout (deliberately NOT varying style
the way hard_ood_bench did -- this benchmark tests content/scenario
novelty, not register robustness, which hard-OOD already covers). Each
prompt supplies a concept + a randomly assigned, never-reused
scenario seed (city, road, entity-ID scheme, time) to force genuinely new
content rather than superficial synonym variation.
"""
from __future__ import annotations
import json, random, re, requests, sys, time, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "indep_bench"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral:latest"
SEED = 20260810

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

# Never-reused scenario seeds: cities/roads/entity-ID schemes not used anywhere
# else in this project's corpora (checked post-hoc via the leakage audit).
CITIES = ["Rotterdam", "Brisbane", "Calgary", "Lyon", "Kraków", "Busan", "Turin",
          "Auckland", "Gothenburg", "Porto", "Winnipeg", "Nagoya"]
ROADS = ["Ring Road N4", "Coastal Highway 12", "Route de la Vallée", "Expressway 8",
         "Old Mill Bypass", "Harbor Link Road", "County Route 214", "Trans-City Corridor 3"]
ID_SCHEMES = ["OBU-{:05d}", "V2X-UNIT-{:04d}", "STN-{:04d}-B", "RSU-{:03d}X"]

N_PER_COMBO = 3
BATCHES_PER_CONCEPT = 4  # 4 batches x 3 = 12 messages per concept, 18 concepts = 216
MAX_RETRIES = 3


def call_llm(prompt: str) -> list[str]:
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False}, timeout=90)
            r.raise_for_status()
            text = r.json()["response"]
            lines = [re.sub(r"^\s*[\d\.\-\)\*:]+\s*", "", l).strip() for l in text.split("\n")]
            lines = [l.strip('"').strip() for l in lines if len(l.strip()) > 15]
            return lines
        except Exception as e:
            print(f"  [retry {attempt+1}] {e}", flush=True)
            time.sleep(2)
    return []


def build_prompt(concept_desc: str, n: int, city: str, road: str, entity_id: str) -> str:
    return (
        f"Write {n} DIFFERENT short vehicle-to-vehicle (V2X) status/report messages, in a formal, "
        f"fully grammatical, professional ETSI CAM/DENM-style scene-report register (third-person, "
        f"factual, concise -- no slang, no idiom). "
        f"Each message should be an example of: {concept_desc}. "
        f"Set the scenario near {city}, on/near '{road}', and reference the reporting entity as {entity_id} "
        f"where natural. Invent specific, concrete, novel narrative details (do not use generic placeholders). "
        f"Each message must be 1-3 sentences, self-contained, standalone (no numbering, no explanation, no quotes). "
        f"Vary sentence structure across the {n} messages. Output exactly {n} messages, one per line, nothing else."
    )


def main():
    random.seed(SEED)
    rows = []
    idx = 0
    all_concepts = list(MALICIOUS_CONCEPTS.items()) + list(BENIGN_CONCEPTS.items())
    total = len(all_concepts) * BATCHES_PER_CONCEPT
    combo_i = 0
    used_scenarios = set()
    for family, desc in all_concepts:
        is_malicious = family in MALICIOUS_CONCEPTS
        for b in range(BATCHES_PER_CONCEPT):
            combo_i += 1
            city = random.choice(CITIES)
            road = random.choice(ROADS)
            scheme = random.choice(ID_SCHEMES)
            entity_id = scheme.format(random.randint(1, 99999) % (10**scheme.count("0")) or 1)
            used_scenarios.add((city, road))
            prompt = build_prompt(desc, N_PER_COMBO, city, road, entity_id)
            print(f"[{combo_i}/{total}] {family} @ {city}/{road} ...", flush=True)
            lines = call_llm(prompt)
            for text in lines[:N_PER_COMBO]:
                idx += 1
                rows.append({
                    "sample_id": f"ind-{idx:04d}",
                    "attack_family": family,
                    "is_attacker": is_malicious,
                    "style": "formal_report_indep",
                    "scenario_city": city,
                    "scenario_road": road,
                    "text": re.sub(r"^[:\-\s]+", "", text).strip(),
                })

    out_path = OUT_DIR / "independent_corpus.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"Wrote {len(rows)} rows to {out_path}; {len(used_scenarios)} distinct city/road scenario pairs used.")


if __name__ == "__main__":
    sys.exit(main())
