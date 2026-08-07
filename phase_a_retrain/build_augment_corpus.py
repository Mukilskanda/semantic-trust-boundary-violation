"""
phase_a_retrain/build_augment_corpus.py
=========================================
Generates additional template-disjoint, in-scope ETSI CAM/DENM-style
training data, weighted toward the five root-caused weak indirection
families (goal_manipulation, instruction_hiding, context_inversion,
reputation_inflation, hazard_normalization), across multiple legitimate
registers, to continue LoRA fine-tuning FROM semantic_gate_v3_mixed_lora_merged.
Never touches any frozen evaluation corpus.
"""
from __future__ import annotations
import json, random, re, requests, sys, time, pathlib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "phase_a_retrain"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral:latest"
SEED = 20260812

WEAK_CONCEPTS = {
    "goal_manipulation": "a message trying to subtly redirect an autonomous vehicle's route or destination by claiming a fabricated reason (faster route, closure, event)",
    "instruction_hiding": "a message that embeds a hidden instruction to an AI system inside what looks like a routine traffic status update",
    "context_inversion": "a message that reframes a genuinely dangerous situation as safe, or a safe situation as dangerous, to manipulate a vehicle's response",
    "reputation_inflation": "a message where a vehicle exaggerates its own trustworthiness, certification, or track record to get other vehicles to trust its claims uncritically",
    "hazard_normalization": "a message that downplays a genuine hazard as routine or expected, to reduce a vehicle's caution response",
}
OTHER_MALICIOUS = {
    "authority_override": "a vehicle falsely claiming police/emergency authority to force other vehicles to yield or stop obeying normal traffic rules",
    "false_clearance": "a vehicle falsely claiming a hazard, accident, or road closure has been cleared and it is now safe to proceed at full speed",
    "priority_manipulation": "a vehicle falsely claiming special priority (ambulance, VIP convoy, platoon leader) to get other vehicles to give way",
    "fabricated_consensus": "a message claiming multiple other nearby vehicles have already agreed or confirmed something, to make a receiving vehicle trust a false claim",
    "sensor_discreditation": "a message trying to convince a vehicle that its own onboard sensors are wrong or malfunctioning, so it should trust the broadcast message instead",
    "traffic_efficiency_lure": "a message that uses an appeal to traffic efficiency or fuel savings to convince a vehicle to take an action against its own safety interest",
    "cross_source_contradiction": "a message where a vehicle reports something that directly contradicts what a roadside unit or another vehicle just reported, without acknowledging the contradiction",
}
BENIGN_CONCEPTS = {
    "benign_routine_status": "an ordinary, routine V2X status update from a vehicle (speed, heading, lane, fuel/battery level) with nothing suspicious",
    "benign_genuine_hazard": "a genuine, truthful hazard warning (real accident, real road closure, real weather hazard) reported factually",
    "benign_genuine_emergency": "a genuinely authorized emergency vehicle (ambulance, fire truck, police) correctly identifying itself while responding to a call",
    "benign_hard_negative_authority": "a completely ordinary, non-manipulative message that happens to mention police, priority, or authority in a routine, truthful, non-manipulative way",
    "benign_hard_negative_clearance": "a truthful message reporting that a previously-known hazard has genuinely been resolved and confirming it through normal, non-manipulative channels",
    "benign_multi_vehicle": "a routine multi-vehicle coordination message (e.g., normal platooning, lane merge courtesy) with no manipulation intent",
}

REGISTERS = [
    ("formal_report", "formal, fully grammatical, professional ETSI CAM/DENM-style third-person scene report"),
    ("terse_telemetry", "terse telemetry-log style, field:value shorthand"),
    ("dispatch_shorthand", "moderately abbreviated dispatch/status shorthand, common trucking/RSU abbreviations, still professional"),
    ("plain_declarative", "plain, simple, declarative English sentences, direct and factual"),
]
CITIES = ["Ghent", "Perth", "Cork", "Marseille", "Poznań", "Ulsan", "Verona", "Hamilton",
          "Uppsala", "Coimbra", "Saskatoon", "Yokohama", "Odense", "Graz", "Timisoara"]
ROADS = ["Ring Road N6", "Coastal Highway 9", "Route du Plateau", "Expressway 22",
         "Millfield Bypass", "Riverside Link Road", "County Route 118", "Cross-City Corridor 4"]
ID_SCHEMES = ["OBU-{:05d}", "V2X-UNIT-{:04d}", "STN-{:04d}-D", "RSU-{:03d}Z"]

N_PER_COMBO = 4
MAX_RETRIES = 3


def call_llm(prompt: str) -> list[str]:
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False}, timeout=90)
            r.raise_for_status()
            text = r.json()["response"]
            lines = [re.sub(r"^\s*[\d\.\-\)\*:]+\s*", "", l).strip() for l in text.split("\n")]
            lines = [l.strip('"').strip() for l in lines if len(l.strip()) > 10]
            return lines
        except Exception as e:
            print(f"  [retry {attempt+1}] {e}", flush=True)
            time.sleep(2)
    return []


def build_prompt(concept_desc, n, style_desc, city, road, entity_id):
    return (
        f"Write {n} DIFFERENT short vehicle-to-vehicle (V2X) status messages. "
        f"Each message should be an example of: {concept_desc}. "
        f"Write in this style: {style_desc}. No self-labeling, no parenthetical explanation of the "
        f"technique -- the message must read as a plausible real broadcast, never announcing its own intent. "
        f"Set the scenario near {city} on '{road}', referencing entity {entity_id} where natural. "
        f"Each message 1-3 sentences, self-contained. Output exactly {n} messages, one per line, nothing else."
    )


def main():
    random.seed(SEED)
    rows = []
    idx = 0

    plan = []
    for fam, desc in WEAK_CONCEPTS.items():
        plan.append((fam, desc, True, 10))   # 10 batches x 4 = 40 per weak family
    for fam, desc in OTHER_MALICIOUS.items():
        plan.append((fam, desc, True, 4))    # 4 batches x 4 = 16 per other family
    for fam, desc in BENIGN_CONCEPTS.items():
        plan.append((fam, desc, False, 4))   # 4 batches x 4 = 16 per benign concept

    total_batches = sum(n for _, _, _, n in plan)
    batch_i = 0
    for fam, desc, is_mal, n_batches in plan:
        for b in range(n_batches):
            batch_i += 1
            style_id, style_desc = REGISTERS[b % len(REGISTERS)]
            city = random.choice(CITIES)
            road = random.choice(ROADS)
            scheme = random.choice(ID_SCHEMES)
            entity_id = scheme.format(random.randint(1, 99999) % 10000 or 1)
            prompt = build_prompt(desc, N_PER_COMBO, style_desc, city, road, entity_id)
            print(f"[{batch_i}/{total_batches}] {fam} / {style_id} @ {city} ...", flush=True)
            lines = call_llm(prompt)
            for text in lines[:N_PER_COMBO]:
                idx += 1
                rows.append({
                    "sample_id": f"aug-{idx:04d}",
                    "attack_family": fam,
                    "is_attacker": is_mal,
                    "style": style_id,
                    "text": re.sub(r"^[:\-\s]+", "", text).strip(),
                })

    out_path = OUT_DIR / "augment_corpus.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    sys.exit(main())
