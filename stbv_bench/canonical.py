"""
stbv_bench/canonical.py
========================
Step 2 of the STBV-Bench pipeline: "Canonical Message Representation."

Converts one REAL VeReMi Extension flat report (as emitted by
import_veremi.py: {sender, x, y, speed, heading, timestamp, is_attacker,
veremi_attacker_type, source}) into this repo's native nested ETSI CAM
message schema (matching test_messages/benign/normal_car.json and
semantic_evaluation/semantic_attack_generator.py's schema), WITHOUT altering
any kinematic value -- position/speed/heading are carried through exactly,
only re-encoded into ETSI fixed-point units and this repo's field layout.

This is the "real dataset" half of STBV-Bench's honesty contract: unlike
semantic_evaluation's fully-synthetic kinematics, every STBV-Bench message's
motion is a real recorded vehicle trajectory from the VeReMi Extension public
dataset (van der Heijden et al., SecureComm 2018; Kamel et al., IEEE ICC
2020), not invented. Only the free-text scene-context fields (which VeReMi
does not have at all -- it carries no message text) are populated by the
semantic transformation engine (stbv_bench/transformations.py).
"""
from __future__ import annotations

import math
from typing import Any, Dict

# Same reference origin convention as scenario_generation/generator.py and
# semantic_evaluation/semantic_attack_generator.py, so STBV-Bench messages
# are drop-in compatible with every existing fixture-consuming script.
BASE_LAT_FIXED = 485512345      # ETSI 1e-7 deg
BASE_LON_FIXED = 96123456
_LAT_DEG_PER_M = 1.0 / 111_132.9
_LON_DEG_PER_M = 1.0 / (111_319.9 * math.cos(math.radians(BASE_LAT_FIXED * 1e-7)))


def veremi_report_to_canonical(
    report: Dict[str, Any],
    *,
    station_id: int,
    station_type: int = 5,
) -> Dict[str, Any]:
    """Converts one VeReMi flat report into this repo's nested CAM schema.

    `report["x"]`/`report["y"]` are VeReMi's local Cartesian meters
    (relative to the simulation's own origin, not this repo's ETSI origin).
    Since only relative motion/consistency matters to B1/MBD/CP (confirmed
    by reading bridges/message_adapter.py: it re-projects everything to a
    single local origin anyway), we place VeReMi's (x, y) onto this repo's
    standard ETSI reference origin via the same meters-per-degree constants
    scenario_generation/generator.py uses -- an origin shift, not a
    kinematic alteration. `report["speed"]` (VeReMi m/s) and
    `report["heading"]` (VeReMi degrees) are carried through unchanged
    except for the unit re-encodings ETSI's wire format requires
    (cm/s, 0.1-degree units) -- confirmed against
    bridges/message_adapter.py's own inverse conversions (speed_kmh = speed
    * 0.01 * 3.6 when abs(speed) > 300, i.e. it expects raw ETSI cm/s; we
    write exactly that unit here).
    """
    x = float(report["x"])
    y = float(report["y"])
    speed_mps = float(report["speed"])
    heading_deg = float(report["heading"]) % 360.0
    timestamp = float(report["timestamp"])

    lat_fixed = int(BASE_LAT_FIXED + (y * _LAT_DEG_PER_M) * 1e7)
    lon_fixed = int(BASE_LON_FIXED + (x * _LON_DEG_PER_M) * 1e7)

    return {
        "header": {"station_id": station_id, "message_id": 1},
        "cam": {
            "generation_delta_time": round(timestamp * 1000.0 % 65536, 2),
            "cam_parameters": {
                "basic_container": {
                    "station_type": station_type,
                    "reference_position": {"latitude": lat_fixed, "longitude": lon_fixed},
                },
                "high_frequency_container": {
                    "basic_vehicle_container_high_frequency": {
                        "speed": int(round(speed_mps * 100)),          # ETSI: 0.01 m/s units
                        "heading": int(round(heading_deg * 10)) % 3600,  # ETSI: 0.1 deg units
                        "yaw_rate": 0,
                        "steering_wheel_angle": 0,
                        "lateral_acceleration": 0,
                        "longitudinal_acceleration": 0,
                    }
                },
            },
        },
        "certificate_id": f"CERT_{station_type}_{station_id}",
        "cert_id": f"CERT_{station_type}_{station_id}",
        "local_perception": {"camera": "CLEAR", "radar": "CLEAR", "lidar": "CLEAR"},
        "scene_context": {"peer_reports": [], "rsu_messages": []},
        # Provenance -- VeReMi's OWN kinematic ground truth, preserved
        # unchanged. This is NOT the STBV-Bench attack label (see
        # generator.py) -- it is carried through purely as provenance so a
        # reader can see this message's real dataset origin and whether
        # VeReMi itself considered its sender a kinematic attacker.
        "_veremi_provenance": {
            "sender": report.get("sender"),
            "veremi_x": x, "veremi_y": y,
            "veremi_speed_mps": speed_mps, "veremi_heading_deg": heading_deg,
            "veremi_timestamp": timestamp,
            "veremi_is_attacker": bool(report.get("is_attacker", False)),
            "veremi_attacker_type": report.get("veremi_attacker_type", 0),
        },
    }
