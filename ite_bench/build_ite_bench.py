"""
ite_bench/build_ite_bench.py
=============================
Integrated Trust Evaluation Benchmark (ITE-Bench): a ~10,000-sample
ablation benchmark balanced across the three trust layers this
architecture's ablation study is meant to characterize, unlike
STBV-Bench v1 (which is deliberately semantic-only per its own threat
model, Section III of the paper).

Each sample is a dict: {sample_id, layer, attack_family, is_attacker,
messages: [msg, ...]}. `messages` is the exact input to
`ISCEPipeline.run(messages)` -- a chronological window whose LAST message
is the one scored; earlier messages (when present) establish real MBD
history within the SAME pipeline.run() call, since orchestrator.py's
_run_mbd() pushes messages[:-1] into the shared VehicleHistoryStore
before scoring messages[-1]. This is required for B2/MBD-focused samples
to be scoreable at all: MBD's kinematic/replay/Sybil checks are
history-relative by design and cannot fire against a message with no
prior context (see ABLATION_AUDIT.md).

- B1-focused samples: single message, real B1-triggering defects
  (missing fields, out-of-range physical values per B1's own plausibility
  bounds, station_type/message_type policy violations, negative
  timestamps, certificate-rotation churn windows, replay windows).
- B2-focused samples: 2-5 message windows, real MBD-triggering kinematics
  (speed/accel/heading-rate jumps between B1's looser bounds and MBD's
  tighter ones, so B1 does NOT also fire; Sybil near-identical positions
  across distinct station_ids; multi-reporter collusion windows).
- B3-focused samples: single message, reusing the existing, already
  leakage-audited semantic taxonomy (benchmark/v25c_compositional.py's
  malicious families), rendered into scene_context.peer_reports exactly
  as STBV-Bench v1 does -- NOT drawn from v1 itself (avoids overlap),
  and NOT drawn from v2.5b (kept reserved as the held-out eval set).
- Benign: single clean messages and clean windows, proportionally split
  the same way, so B1/B2/B3-context benign traffic is represented.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmark"))

from v25c_compositional import MALICIOUS_CORE, realise, slots, pick_core  # noqa: E402

OUT_DIR = ROOT / "ite_bench" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SEED = 20260808

# ETSI station type codes (matches isce_config.yaml station_types)
ST_PASSENGER_CAR = 5
ST_RSU = 15
ST_BUS = 6
# ETSI message type codes (matches isce_config.yaml message_types)
MT_CAM = 1
MT_DENM = 2
MT_MAPEM = 5
MT_SPATEM = 6
MT_SREM = 7
MT_RTCMEM = 28

BASE_LAT = 485512345   # matches existing test-fixture convention
BASE_LON = 96123456

# 1 degree latitude =~ 111,320 m => 1 unit of 1e-7-degree ETSI fixed-point
# =~ 0.0111320 m. Used to keep BENIGN windows' claimed position displacement
# consistent with claimed speed, so MBD's "constant position vs. claimed
# speed" check does not spuriously fire on legitimate traffic -- this was
# a real bug caught by the smoke test (see ABLATION_DATASET_AUDIT.md):
# an early draft used near-zero position deltas for ALL windows, including
# benign ones, which falsely triggered MBD on clean traffic.
_M_PER_DEGLAT = 111_320.0
_UNITS_PER_METER = 1e7 / _M_PER_DEGLAT


def _advance_position(lat, lon, speed_cms, dt_ms):
    """Returns (new_lat, new_lon) displaced consistently with a claimed
    speed (0.01 m/s units) over dt_ms milliseconds -- straight-line, +lat."""
    speed_ms = speed_cms / 100.0
    dt_s = dt_ms / 1000.0
    displacement_m = speed_ms * dt_s
    delta_units = int(displacement_m * _UNITS_PER_METER)
    return lat + delta_units, lon


def _cam(station_id, message_id, station_type, lat, lon, speed_cms, heading_dhg,
         accel_cms2=0, yaw_rate=0, ts=1000, cert_id=None, peer_reports=None,
         rsu_messages=None):
    """Builds one nested CAM message in this repo's native schema
    (matches data/stbv_bench/v1's transformed_message shape exactly)."""
    return {
        "header": {"station_id": station_id, "message_id": message_id},
        "cam": {
            "generation_delta_time": ts,
            "cam_parameters": {
                "basic_container": {
                    "station_type": station_type,
                    "reference_position": {"latitude": lat, "longitude": lon},
                },
                "high_frequency_container": {
                    "basic_vehicle_container_high_frequency": {
                        "speed": speed_cms, "heading": heading_dhg,
                        "yaw_rate": yaw_rate, "steering_wheel_angle": 0,
                        "lateral_acceleration": 0, "longitudinal_acceleration": accel_cms2,
                    }
                },
            },
        },
        "certificate_id": cert_id or f"CERT_{station_type}_{station_id}",
        "cert_id": cert_id or f"CERT_{station_type}_{station_id}",
        "local_perception": {"camera": "CLEAR", "radar": "CLEAR", "lidar": "CLEAR"},
        "scene_context": {"peer_reports": peer_reports or [], "rsu_messages": rsu_messages or []},
    }


# ===========================================================================
# B1-FOCUSED: single-message, real B1 plausibility/structural/policy triggers
# ===========================================================================
def gen_b1_missing_fields(rng, sid):
    m = _cam(sid, MT_CAM, ST_PASSENGER_CAR, BASE_LAT, BASE_LON, 1200, 900, ts=1000 + sid)
    field_to_drop = rng.choice(["station_id", "timestamp", "latitude", "station_type"])
    if field_to_drop == "station_id":
        del m["header"]["station_id"]
    elif field_to_drop == "timestamp":
        del m["cam"]["generation_delta_time"]
    elif field_to_drop == "latitude":
        del m["cam"]["cam_parameters"]["basic_container"]["reference_position"]["latitude"]
    elif field_to_drop == "station_type":
        del m["cam"]["cam_parameters"]["basic_container"]["station_type"]
    return m, "malformed_missing_field"


def gen_b1_invalid_coordinates(rng, sid):
    bad_lat = rng.choice([950_000_000, -950_000_000, 999_999_999])
    m = _cam(sid, MT_CAM, ST_PASSENGER_CAR, bad_lat, BASE_LON, 1200, 900, ts=1000 + sid)
    return m, "invalid_coordinates"


def gen_b1_impossible_speed(rng, sid):
    # B1's own max_speed = 8330 (0.01 m/s units, ~300 km/h). Well beyond it.
    m = _cam(sid, MT_CAM, ST_PASSENGER_CAR, BASE_LAT, BASE_LON, rng.randint(20000, 60000), 900, ts=1000 + sid)
    return m, "impossible_speed"


def gen_b1_impossible_acceleration(rng, sid):
    # B1's own max_acceleration = 1500 (0.01 m/s^2, ~15 m/s^2). Well beyond it.
    m = _cam(sid, MT_CAM, ST_PASSENGER_CAR, BASE_LAT, BASE_LON, 1200, 900,
              accel_cms2=rng.randint(3000, 9000), ts=1000 + sid)
    return m, "impossible_acceleration"


def gen_b1_invalid_heading(rng, sid):
    bad_heading = rng.choice([-100, 5000, 99999])
    m = _cam(sid, MT_CAM, ST_PASSENGER_CAR, BASE_LAT, BASE_LON, 1200, bad_heading, ts=1000 + sid)
    return m, "invalid_heading"


def gen_b1_negative_timestamp(rng, sid):
    m = _cam(sid, MT_CAM, ST_PASSENGER_CAR, BASE_LAT, BASE_LON, 1200, 900, ts=-rng.randint(1, 5000))
    return m, "negative_timestamp"


def gen_b1_spoofed_identity(rng, sid):
    # Passenger car claiming an infrastructure-only message type -- blocked
    # by isce_config.yaml's b1_scsv policy rules (default_policy=block,
    # explicit block rules for passengerCar+{SREM,SPATEM,MAPEM,RTCMEM}).
    mt = rng.choice([MT_SPATEM, MT_MAPEM, MT_SREM, MT_RTCMEM])
    m = _cam(sid, mt, ST_PASSENGER_CAR, BASE_LAT, BASE_LON, 1200, 900, ts=1000 + sid)
    return m, "spoofed_authority_identifier"


def gen_b1_replay_window(rng, sid):
    # Same (station_id, message_id, timestamp) repeated verbatim -- B1's
    # replay cache flags the second occurrence.
    msg1 = _cam(sid, 7, ST_PASSENGER_CAR, BASE_LAT, BASE_LON, 1200, 900, ts=5000)
    msg2 = dict(msg1)  # exact replay
    return [msg1, msg2], "replay_with_stale_credential_state"


def gen_b1_cert_rotation_anomaly(rng, sid):
    # >3 certificate changes within the 60s rotation window -- flagged as
    # a certificate-rotation anomaly by B1's _VehicleStateManager.
    msgs = []
    for i in range(5):
        msgs.append(_cam(sid, MT_CAM, ST_PASSENGER_CAR, BASE_LAT, BASE_LON, 1200, 900,
                          ts=1000 + i * 2000, cert_id=f"CERT_ROTATE_{sid}_{i}"))
    return msgs, "certificate_chain_instability"


def gen_b1_benign(rng, sid):
    m = _cam(sid, MT_CAM, ST_PASSENGER_CAR, BASE_LAT + rng.randint(-500, 500),
              BASE_LON + rng.randint(-500, 500), rng.randint(800, 1800), rng.randint(0, 3599),
              ts=1000 + sid)
    return m, "benign_control"


B1_ATTACK_GENERATORS = [
    gen_b1_missing_fields, gen_b1_invalid_coordinates, gen_b1_impossible_speed,
    gen_b1_impossible_acceleration, gen_b1_invalid_heading, gen_b1_negative_timestamp,
    gen_b1_spoofed_identity, gen_b1_replay_window, gen_b1_cert_rotation_anomaly,
]


# ===========================================================================
# B2-FOCUSED: multi-message windows, real MBD history-relative triggers.
# Values chosen BETWEEN B1's looser bounds and MBD's tighter ones so these
# fire ONLY on MBD, not on B1 -- genuinely isolating the behavioral layer.
# ===========================================================================
def gen_b2_speed_jump(rng, sid):
    # MBD's speed_check flags > 180 km/h = 5000 (0.01 m/s units); B1's own
    # bound is 8330. 6000-7500 clears MBD's threshold but stays under B1's.
    msg1 = _cam(sid, MT_CAM, ST_PASSENGER_CAR, BASE_LAT, BASE_LON, 1200, 900, ts=1000)
    msg2 = _cam(sid, MT_CAM, ST_PASSENGER_CAR, BASE_LAT + 5, BASE_LON + 5,
                rng.randint(6000, 7500), 900, ts=2000)
    return [msg1, msg2], "impossible_velocity_jump"


def gen_b2_impossible_acceleration_mbd(rng, sid):
    # MBD's MAX_ACCEL=6.0 m/s^2 (derived from flat speed delta/dt); stay
    # under B1's 15 m/s^2 raw-field bound so only MBD fires.
    msg1 = _cam(sid, MT_CAM, ST_PASSENGER_CAR, BASE_LAT, BASE_LON, 1000, 900, ts=1000)
    msg2 = _cam(sid, MT_CAM, ST_PASSENGER_CAR, BASE_LAT + 2, BASE_LON + 2, 2800, 900, ts=1500)
    return [msg1, msg2], "impossible_acceleration_behavioral"


def gen_b2_heading_rate(rng, sid):
    msg1 = _cam(sid, MT_CAM, ST_PASSENGER_CAR, BASE_LAT, BASE_LON, 1200, 200, ts=1000)
    msg2 = _cam(sid, MT_CAM, ST_PASSENGER_CAR, BASE_LAT, BASE_LON, 1200, 3400, ts=1300)
    return [msg1, msg2], "temporal_heading_inconsistency"


def gen_b2_sybil(rng, sid):
    # Two DISTINCT station_ids report near-identical position/kinematics
    # at the same time -- MBD's sybil_score fires on the second.
    lat, lon = BASE_LAT + rng.randint(-50, 50), BASE_LON + rng.randint(-50, 50)
    msg1 = _cam(sid, MT_CAM, ST_PASSENGER_CAR, lat, lon, 1200, 900, ts=4000)
    msg2 = _cam(sid + 500000, MT_CAM, ST_PASSENGER_CAR, lat + 2, lon + 2, 1205, 902, ts=4010)
    return [msg1, msg2], "sybil_behavior"


def gen_b2_collusion(rng, sid):
    # 3+ distinct senders co-reporting the same claimed event in a short
    # window -- MBD's collusion_score, which requires a top-level "event"
    # field matching across co-reporters (mbd_layer.py's collusion check).
    lat, lon = BASE_LAT + rng.randint(-50, 50), BASE_LON + rng.randint(-50, 50)
    msgs = []
    for i in range(4):
        m = _cam(sid + i * 700000, MT_CAM, ST_PASSENGER_CAR, lat + i, lon + i,
                  1200, 900, ts=4000 + i * 5)
        m["event"] = "hazard_on_road"
        msgs.append(m)
    return msgs, "multi_sender_collusion"


def gen_b2_replay_pattern(rng, sid):
    # Identical position+speed pattern repeated verbatim later in the
    # window with a DIFFERENT message_id (so B1's own message_id/timestamp
    # replay cache does not fire) -- exercises MBD's own replay_score,
    # which reasons over position/pattern repetition in history rather
    # than raw (station_id, message_id, timestamp) equality.
    lat, lon = BASE_LAT + rng.randint(-50, 50), BASE_LON + rng.randint(-50, 50)
    msg1 = _cam(sid, 7, ST_PASSENGER_CAR, lat, lon, 1200, 900, ts=6000)
    msg2 = _cam(sid, 8, ST_PASSENGER_CAR, lat, lon, 1200, 900, ts=6500)
    msg3 = _cam(sid, 9, ST_PASSENGER_CAR, lat, lon, 1200, 900, ts=7000)
    return [msg1, msg2, msg3], "behavioral_replay_pattern"


def gen_b2_trust_history_anomaly(rng, sid):
    # Erratic oscillating speed profile across a longer window -- no
    # single jump crosses a hard threshold, but the pattern is atypical.
    msgs = []
    speeds = [1000, 4000, 900, 4200, 1000]
    for i, sp in enumerate(speeds):
        msgs.append(_cam(sid, MT_CAM, ST_PASSENGER_CAR, BASE_LAT, BASE_LON, sp, 900, ts=1000 + i * 1000))
    return msgs, "trust_history_anomaly"


def gen_b2_benign_window(rng, sid):
    msgs = []
    lat, lon = BASE_LAT + rng.randint(-500, 500), BASE_LON + rng.randint(-500, 500)
    speed = rng.randint(900, 1600)
    ts = 1000
    for i in range(rng.choice([2, 3])):
        dt_ms = 0 if i == 0 else 1000
        lat, lon = _advance_position(lat, lon, speed, dt_ms)
        msgs.append(_cam(sid, MT_CAM, ST_PASSENGER_CAR, lat, lon,
                          speed + rng.randint(-30, 30), 900, ts=ts))
        ts += 1000
    return msgs, "benign_control"


B2_ATTACK_GENERATORS = [
    gen_b2_speed_jump, gen_b2_impossible_acceleration_mbd, gen_b2_heading_rate,
    gen_b2_sybil, gen_b2_collusion, gen_b2_replay_pattern, gen_b2_trust_history_anomaly,
]


# ===========================================================================
# B3-FOCUSED: single message, reusing the existing leakage-audited semantic
# taxonomy (v2.5c's malicious families), NOT drawn from v1 or v2.5b.
# ===========================================================================
B3_FAMILY_SUBSET = [
    "authority_override", "false_clearance", "priority_manipulation",
    "sensor_discreditation", "context_inversion", "cross_source_contradiction",
]


def gen_b3_attack(rng, sid, family):
    s = slots(rng)
    core, mood = pick_core(rng, MALICIOUS_CORE, family)
    text = realise(rng, core, s)
    m = _cam(sid, MT_CAM, ST_PASSENGER_CAR, BASE_LAT, BASE_LON, 1200, 900, ts=1000 + sid,
              peer_reports=[text])
    return m, family


def gen_b3_benign(rng, sid):
    texts = [
        "Traffic moving normally on the corridor.",
        "No incidents reported in this segment.",
        "Conditions clear, flow steady.",
    ]
    m = _cam(sid, MT_CAM, ST_PASSENGER_CAR, BASE_LAT, BASE_LON, 1200, 900, ts=1000 + sid,
              peer_reports=[rng.choice(texts)])
    return m, "benign_control"


# ===========================================================================
def to_record(sample_id, layer, family, is_attacker, messages_or_msg):
    messages = messages_or_msg if isinstance(messages_or_msg, list) else [messages_or_msg]
    return {"sample_id": sample_id, "layer": layer, "attack_family": family,
            "is_attacker": is_attacker, "messages": messages}


def main():
    rng = random.Random(SEED)
    records = []
    sid_counter = 100000

    N_PER_LAYER = 3300   # ~3300 * 3 = 9900, plus benign fill to ~10,000

    # ---- B1: attacks + matched benign ----
    n_b1_attack = int(N_PER_LAYER * 0.75)
    n_b1_benign = N_PER_LAYER - n_b1_attack
    for i in range(n_b1_attack):
        sid_counter += 1
        gen = B1_ATTACK_GENERATORS[i % len(B1_ATTACK_GENERATORS)]
        msg, fam = gen(rng, sid_counter)
        records.append(to_record(f"ite-b1-{i:05d}", "B1", fam, True, msg))
    for i in range(n_b1_benign):
        sid_counter += 1
        msg, fam = gen_b1_benign(rng, sid_counter)
        records.append(to_record(f"ite-b1-benign-{i:05d}", "B1", fam, False, msg))

    # ---- B2: attacks + matched benign ----
    n_b2_attack = int(N_PER_LAYER * 0.75)
    n_b2_benign = N_PER_LAYER - n_b2_attack
    for i in range(n_b2_attack):
        sid_counter += 1
        gen = B2_ATTACK_GENERATORS[i % len(B2_ATTACK_GENERATORS)]
        msgs, fam = gen(rng, sid_counter)
        records.append(to_record(f"ite-b2-{i:05d}", "B2", fam, True, msgs))
    for i in range(n_b2_benign):
        sid_counter += 1
        msgs, fam = gen_b2_benign_window(rng, sid_counter)
        records.append(to_record(f"ite-b2-benign-{i:05d}", "B2", fam, False, msgs))

    # ---- B3: attacks + matched benign ----
    n_b3_attack = int(N_PER_LAYER * 0.75)
    n_b3_benign = N_PER_LAYER - n_b3_attack
    for i in range(n_b3_attack):
        sid_counter += 1
        family = B3_FAMILY_SUBSET[i % len(B3_FAMILY_SUBSET)]
        msg, fam = gen_b3_attack(rng, sid_counter, family)
        records.append(to_record(f"ite-b3-{i:05d}", "B3", fam, True, msg))
    for i in range(n_b3_benign):
        sid_counter += 1
        msg, fam = gen_b3_benign(rng, sid_counter)
        records.append(to_record(f"ite-b3-benign-{i:05d}", "B3", fam, False, msg))

    rng.shuffle(records)

    out_path = OUT_DIR / "ite_bench.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    n_attack = sum(1 for r in records if r["is_attacker"])
    manifest = {
        "benchmark": "Integrated Trust Evaluation Benchmark (ITE-Bench)",
        "seed": SEED,
        "n_total": len(records),
        "n_attack": n_attack, "n_benign": len(records) - n_attack,
        "prevalence_malicious": n_attack / len(records),
        "layer_counts": {L: sum(1 for r in records if r["layer"] == L) for L in ("B1", "B2", "B3")},
        "family_counts": {},
        "usage_policy": "Ablation-only benchmark, distinct from and non-overlapping with "
                        "STBV-Bench v1, v2.5, v2.5b, and v2.5c. B3-focused samples reuse "
                        "v2.5c's malicious-family template bank (fresh seed/slot draws), "
                        "never v1's or v2.5b's own text.",
    }
    for r in records:
        manifest["family_counts"][r["attack_family"]] = manifest["family_counts"].get(r["attack_family"], 0) + 1
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    print(f"\n[ok] {out_path}")


if __name__ == "__main__":
    main()
