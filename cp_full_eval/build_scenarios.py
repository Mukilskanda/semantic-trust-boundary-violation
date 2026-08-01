#!/usr/bin/env python3
"""
build_scenarios.py
====================
Constructs a realistic, event-labeled, multi-vehicle Cooperative
Perception (CP) benchmark -- CP's own architecture and evaluation
methodology are unchanged; this only supplies data of the shape CP was
designed to consume (multiple vehicles reporting on the SAME claimed
event, in the same window) but which no benchmark evaluated so far in
this project actually contains (STBV-Bench never populates the event
field at all; the pre-existing scenarios/*.json fixtures have only 3
event-labeled messages total, across all 120).

Five scenario categories, each testing a different, real CP mechanism
(not just "make CP look good"):

  A. genuine_multi_vehicle_corroboration (benign) -- realistic sensor
     noise only, no attacker. Tests: does CP avoid false positives when
     honest vehicles genuinely agree.
  B. lone_fabricator_vs_honest_majority (malicious) -- one attacker
     among an honest majority, spatially/kinematically inconsistent with
     them. Tests: does CP's contradiction channel catch a lone fabricator
     that B1/MBD (which only ever see one message at a time) cannot.
  C. colluding_minority_consistent_fabrication (malicious) -- 3 attackers
     agree tightly with each other but contradict a 5-vehicle honest
     majority. Tests the literature-documented weakness (Zhang et al.,
     data-fabrication attacks) that coordinated collusion can partially
     defeat pure statistical consistency fusion -- an honest test of a
     known limitation, not hidden.
  D. sparse_reporting_uncertainty (benign, low diversity) -- only 2
     unique senders. Tests: does CP correctly route low corroboration to
     UNCERTAINTY (Theta mass) rather than false DISBELIEF.
  E. natural_sensor_noise_no_attacker (benign edge case) -- moderate,
     honest spatial spread from different vantage points on one real,
     large/ambiguous event. Tests: does CP's fixed spread/20 formula
     wrongly penalize honest variance as if it were attack signal.

All messages use the same nested ETSI-CAM-shaped schema as the existing,
already-verified scenarios/*.json fixtures (header/cam/cam_parameters/...),
so B1/SCSV validates them exactly as it does today -- no new message
format, no architecture change. Positions are given as plain decimal
degrees (skips ETSI fixed-point conversion, which to_flat_report already
handles by magnitude, not by a format flag).
"""
import json, pathlib, random

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "scenarios"
MASTER_SEED = 20260803

BASE_LAT = 48.5512
BASE_LON = 9.6123
# ~1e-5 deg lat/lon at this latitude is roughly 1.0-1.1 m
DEG_PER_M = 1.0 / 111_000.0


def make_msg(station_id, msg_id, t_ms, lat, lon, speed_kmh, heading_deg,
             is_attacker, event=None):
    m = {
        "header": {"station_id": station_id, "message_id": msg_id},
        "cam": {
            "generation_delta_time": t_ms,
            "cam_parameters": {
                "basic_container": {
                    "station_type": 5,
                    "reference_position": {"latitude": lat, "longitude": lon},
                },
                "high_frequency_container": {
                    "basic_vehicle_container_high_frequency": {
                        "speed": speed_kmh, "heading": heading_deg % 360.0,
                        "yaw_rate": 0, "steering_wheel_angle": 0,
                        "lateral_acceleration": 0, "longitudinal_acceleration": 0,
                    }
                },
            },
        },
        "is_attacker": is_attacker,
    }
    if event is not None:
        m["event"] = event
    return m


def scene_A(rng, idx):
    """Genuine multi-vehicle corroboration, benign, n=6."""
    event = f"hazardous_location_A{idx}"
    base_speed, base_heading = rng.uniform(45, 90), rng.uniform(0, 360)
    msgs = []
    for i in range(6):
        lat = BASE_LAT + rng.uniform(-6, 6) * DEG_PER_M
        lon = BASE_LON + rng.uniform(-6, 6) * DEG_PER_M
        speed = base_speed + rng.uniform(-3, 3)
        heading = base_heading + rng.uniform(-5, 5)
        msgs.append(make_msg(6000 + idx * 10 + i, i, i * 100, lat, lon, speed, heading,
                              False, event=event))
    return {"category": "genuine_multi_vehicle_corroboration", "expected_cp_effect": "no_false_positive",
            "messages": msgs}


def scene_B(rng, idx):
    """Lone fabricator vs. honest majority, malicious, n=6 (5 honest + 1 attacker)."""
    event = f"obstacle_on_road_B{idx}"
    base_speed, base_heading = rng.uniform(50, 100), rng.uniform(0, 360)
    msgs = []
    for i in range(5):
        lat = BASE_LAT + rng.uniform(-5, 5) * DEG_PER_M
        lon = BASE_LON + rng.uniform(-5, 5) * DEG_PER_M
        speed = base_speed + rng.uniform(-3, 3)
        heading = base_heading + rng.uniform(-5, 5)
        msgs.append(make_msg(7000 + idx * 10 + i, i, i * 100, lat, lon, speed, heading,
                              False, event=event))
    # attacker: same claimed event, but spatially/kinematically inconsistent
    off_m = rng.choice([-1, 1]) * rng.uniform(70, 140)
    lat_a = BASE_LAT + off_m * DEG_PER_M
    lon_a = BASE_LON + rng.uniform(-5, 5) * DEG_PER_M
    speed_a = base_speed + rng.choice([-1, 1]) * rng.uniform(30, 55)
    heading_a = (base_heading + rng.choice([-1, 1]) * rng.uniform(60, 120)) % 360
    msgs.append(make_msg(7000 + idx * 10 + 5, 5, 500, lat_a, lon_a, speed_a, heading_a,
                          True, event=event))
    return {"category": "lone_fabricator_vs_honest_majority", "expected_cp_effect": "cp_should_catch",
            "messages": msgs}


def scene_C(rng, idx):
    """Colluding minority, consistent with each other, contradicting the honest
    majority, malicious, n=8 (5 honest + 3 colluding attackers)."""
    event = f"road_works_C{idx}"
    base_speed, base_heading = rng.uniform(50, 90), rng.uniform(0, 360)
    msgs = []
    for i in range(5):
        lat = BASE_LAT + rng.uniform(-5, 5) * DEG_PER_M
        lon = BASE_LON + rng.uniform(-5, 5) * DEG_PER_M
        speed = base_speed + rng.uniform(-3, 3)
        heading = base_heading + rng.uniform(-5, 5)
        msgs.append(make_msg(8000 + idx * 10 + i, i, i * 100, lat, lon, speed, heading,
                              False, event=event))
    # 3 colluding attackers: tightly agree with EACH OTHER, but offset from
    # the honest cluster (simulating coordinated fabrication of a shared,
    # false claim about the same named event)
    off_m = rng.choice([-1, 1]) * rng.uniform(60, 100)
    collude_lat = BASE_LAT + off_m * DEG_PER_M
    collude_lon = BASE_LON + rng.uniform(-3, 3) * DEG_PER_M
    collude_speed = base_speed + rng.choice([-1, 1]) * rng.uniform(25, 40)
    collude_heading = (base_heading + rng.choice([-1, 1]) * rng.uniform(40, 70)) % 360
    for j in range(3):
        lat = collude_lat + rng.uniform(-2, 2) * DEG_PER_M
        lon = collude_lon + rng.uniform(-2, 2) * DEG_PER_M
        speed = collude_speed + rng.uniform(-2, 2)
        heading = collude_heading + rng.uniform(-3, 3)
        msgs.append(make_msg(8000 + idx * 10 + 5 + j, 5 + j, (5 + j) * 100, lat, lon,
                              speed, heading, True, event=event))
    return {"category": "colluding_minority_consistent_fabrication",
            "expected_cp_effect": "honest_test_of_known_weakness", "messages": msgs}


def scene_D(rng, idx):
    """Sparse reporting, benign, only 2 unique senders, n=3."""
    event = f"traffic_condition_D{idx}"
    lat0 = BASE_LAT + rng.uniform(-4, 4) * DEG_PER_M
    lon0 = BASE_LON + rng.uniform(-4, 4) * DEG_PER_M
    speed0 = rng.uniform(50, 90)
    heading0 = rng.uniform(0, 360)
    sender_a, sender_b = 9000 + idx * 10, 9000 + idx * 10 + 1
    msgs = [
        make_msg(sender_a, 0, 0, lat0, lon0, speed0, heading0, False, event=event),
        make_msg(sender_b, 1, 100,
                  lat0 + rng.uniform(-3, 3) * DEG_PER_M, lon0 + rng.uniform(-3, 3) * DEG_PER_M,
                  speed0 + rng.uniform(-2, 2), heading0 + rng.uniform(-3, 3), False, event=event),
        make_msg(sender_a, 2, 200,
                  lat0 + rng.uniform(-2, 2) * DEG_PER_M, lon0 + rng.uniform(-2, 2) * DEG_PER_M,
                  speed0 + rng.uniform(-2, 2), heading0 + rng.uniform(-3, 3), False, event=event),
    ]
    return {"category": "sparse_reporting_uncertainty", "expected_cp_effect": "uncertainty_not_disbelief",
            "messages": msgs}


def scene_E(rng, idx):
    """Natural sensor noise, benign, larger honest spread (different
    vantage points on one real, large/ambiguous event), n=6."""
    event = f"accident_E{idx}"
    base_speed, base_heading = rng.uniform(40, 80), rng.uniform(0, 360)
    msgs = []
    for i in range(6):
        lat = BASE_LAT + rng.uniform(-20, 20) * DEG_PER_M
        lon = BASE_LON + rng.uniform(-20, 20) * DEG_PER_M
        speed = base_speed + rng.uniform(-8, 8)
        heading = base_heading + rng.uniform(-15, 15)
        msgs.append(make_msg(10000 + idx * 10 + i, i, i * 150, lat, lon, speed, heading,
                              False, event=event))
    return {"category": "natural_sensor_noise_no_attacker", "expected_cp_effect": "false_positive_risk_test",
            "messages": msgs}


def main():
    rng = random.Random(MASTER_SEED)
    scenes = []
    for i in range(5):
        scenes.append(scene_A(rng, i))
    for i in range(6):
        scenes.append(scene_B(rng, i))
    for i in range(5):
        scenes.append(scene_C(rng, i))
    for i in range(4):
        scenes.append(scene_D(rng, i))
    for i in range(4):
        scenes.append(scene_E(rng, i))

    for i, sc in enumerate(scenes):
        sc["scene_id"] = f"scene_{i:03d}_{sc['category']}"

    manifest = {
        "master_seed": MASTER_SEED,
        "n_scenes": len(scenes),
        "n_messages": sum(len(s["messages"]) for s in scenes),
        "by_category": {},
    }
    for sc in scenes:
        manifest["by_category"].setdefault(sc["category"], {"n_scenes": 0, "n_messages": 0})
        manifest["by_category"][sc["category"]]["n_scenes"] += 1
        manifest["by_category"][sc["category"]]["n_messages"] += len(sc["messages"])

    (OUT / "scenes.json").write_text(json.dumps(scenes, indent=2), encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    print(f"\nWrote {OUT / 'scenes.json'}")


if __name__ == "__main__":
    main()
