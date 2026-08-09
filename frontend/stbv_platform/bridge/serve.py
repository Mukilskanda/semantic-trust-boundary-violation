#!/usr/bin/env python3
"""
frontend/stbv_platform/bridge/serve.py
======================================
FastAPI backend that:
  - Exposes a WebSocket endpoint at /ws (port 8200) for the dashboard.
  - Exposes POST /inject — accepts a vehicle/scene payload, runs it through
    the real ISCEPipeline, and broadcasts the result to all connected WS clients.
  - Exposes GET /health — liveness probe.

Run from the repo root so that `from pipeline.orchestrator import ISCEPipeline`
resolves correctly:

    python -m uvicorn frontend.stbv_platform.bridge.serve:app --host 0.0.0.0 --port 8200

Implementation notes (after reading b1_scsv/models.py, b1_scsv/scsv.py,
pipeline/orchestrator.py):

safe_parse_cam() has a FLAT-DICT SHORTCUT (models.py line 392-409):
    if "x" in raw and "y" in raw and "sender" in raw: ...
This path triggers whenever the message contains those keys, bypassing the
nested CAM structure entirely. It maps:
    station_id  = int(raw["sender"])      <- raises ValueError if sender is non-numeric
    latitude    = float(raw["y"])         <- used directly as ETSI 1e-7-degree units
    longitude   = float(raw["x"])
    speed       = float(raw["speed"])     <- ETSI 0.01 m/s units
    heading     = float(raw["heading"])   <- ETSI 0.1-degree units
    station_type= 5 (passengerCar hardcoded)
    message_id  = 1 (CAM hardcoded)
    certificate_id = f"CERT_{raw['sender']}"
    timestamp   = int(raw["timestamp"])

B1 fatal conditions (from _check_stateful_impl):
    cam is None (parse failure)             -> fatal=True
    station_id / timestamp / latitude /
    longitude / station_type is None        -> fatal=True

B1 recoverable penalties (non-fatal):
    replay detected                         -> -0.30 from validation_score
    stale timestamp (age > freshness_ms)   -> -0.20
    cert rotation anomaly                   -> -0.15
    physics anomaly (recoverable)           -> -0.25

ValidationAssessment.valid (property):
    return not self.fatal and len(self.reasons) == 0
    i.e. True only when absolutely no anomalies occurred.

Orchestrator B1→B2 flow:
    If is_b1_fatal: B2 gets a skip stub with validation_valid=False.
                    B3 also gets an unavailable stub.
    Otherwise: B2 always runs.

Frame field mapping (transparent read of pipeline output):
    layers.B1   <- b1.get("valid") — from _normalize_b1_result which maps
                   ValidationAssessment.valid correctly
    layers.MBD  <- mbd.get("passed") — MBDResult.passed (plausibility_pass
                   AND kinematics_ok AND replay_score < 0.9); False = flag
    layers.B2   <- b2.get("validation_valid") — B1's valid passthrough,
                   then lowered by CP fold when contradiction fires;
                   present in both normal and B1-fatal paths
    layers.CP   <- cp.get("cp_pass") when observations_available=True;
                   False = genuine contradiction flag (not corroboration
                   deficit, which is routed through confidence/uncertainty)
    layers.B3   <- b3.get("available") and b3.get("label") != "BENIGN"
    decision    <- r["decision"] (already the trust_level string from to_dict())
    reason      <- r["reason"]
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[serve] %(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pipeline — loaded once at startup.  Failure is non-fatal: the server stays
# up and /inject returns HTTP 503 until the model is available.
# ---------------------------------------------------------------------------
_pipeline: Optional[Any] = None
_pipeline_error: Optional[str] = None

try:
    from pipeline.orchestrator import ISCEPipeline  # noqa: E402

    log.info("Loading ISCEPipeline (B3 model pre-load may take ~150 s on first run)...")
    _pipeline = ISCEPipeline(enable_mbd=True, enable_cp=True, enable_b3=True)
    log.info("ISCEPipeline ready.")
except Exception as _exc:
    _pipeline_error = str(_exc)
    log.warning(
        "ISCEPipeline import/init failed (%s). "
        "Server will run but /inject will return 503 until the pipeline is available.",
        _exc,
    )

# ---------------------------------------------------------------------------
# FastAPI app + CORS
# ---------------------------------------------------------------------------
app = FastAPI(title="STBV Pipeline Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Connected WebSocket clients
# ---------------------------------------------------------------------------
_clients: Set[WebSocket] = set()


async def _broadcast(payload: str) -> None:
    """Send *payload* to every connected WebSocket client."""
    dead: Set[WebSocket] = set()
    for ws in list(_clients):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


# ---------------------------------------------------------------------------
# Frame builder — reads directly from pipeline output; no overrides.
#
# Field sources (all from the pipeline result dict, nothing fabricated here):
#
#   layers.B1  ← b1["valid"]
#                _normalize_b1_result() in orchestrator.py maps
#                ValidationAssessment.valid correctly (property:
#                  not self.fatal and len(self.reasons) == 0)
#                "flag" when valid is False, "pass" otherwise.
#
#   layers.MBD ← mbd["passed"]  (MBDResult.__init__ sets both ["passed"]
#                and ["mbd_pass"] to the same value)
#                mbd_layer.py line 378:
#                  passed = plausibility_pass and kinematics_ok and (replay_score < 0.9)
#                "skip" when r["mbd"] is None (B1-fatal path or enable_mbd=False)
#                "flag" when mbd["passed"] is False (kinematic/plausibility/replay anomaly)
#                "pass" otherwise
#
#   layers.B2  ← b2["validation_valid"]
#                B2's ExplainabilityReport carries B1's valid as a passthrough
#                (models.py line 36 + explainability.py lines 115/148).
#                After the CP fold in orchestrator.py (lines 638-670), it
#                reflects the combined B1+MBD+CP verdict.
#                Always present: normal path sets it from B2 output;
#                B1-fatal path sets it to False in the skip stub.
#                "flag" when validation_valid is False, "pass" otherwise.
#
#   layers.CP  ← cp["cp_pass"] gated by cp["observations_available"]
#                cp_layer.py line 165:
#                  cp_pass = bool(confidence > 0.7) if observations_available else True
#                Two distinct CP conditions per orchestrator.py docstring (lines 568-594):
#                  - CONTRADICTION (observations_available=True, cp_pass=False):
#                    genuine negative evidence → "flag"
#                  - CORROBORATION DEFICIT (observations_available=False or
#                    few/low-diversity reports): absence of evidence, not an
#                    attack → surfaces as uncertainty via confidence axis, NOT "flag"
#                "skip" when r["cp"] is None (B1-fatal path or enable_cp=False)
#                "flag" when cp["observations_available"] and not cp["cp_pass"]
#                "pass" otherwise (corroboration deficit stays at "pass")
#
#   layers.B3  ← b3["available"] and b3["label"] != "BENIGN"
#                "flag" when B3 ran and flagged non-BENIGN;
#                "pass" when B3 is unavailable, not run, or returned BENIGN.
#
#   decision   ← r["decision"]  (trust_level string from FinalTrustDecision.to_dict())
#
#   reason     ← r["reason"]    (reasoning string from FinalTrustDecision.to_dict())
#
# Mirror of result_to_frame() in carla_bridge.py — kept in sync intentionally.
# ---------------------------------------------------------------------------
def _result_to_frame(rec: Dict[str, Any], r: Dict[str, Any]) -> Dict[str, Any]:
    """Map an inject record + pipeline result dict to the WebSocket frame shape.

    All frame fields are derived directly from the pipeline's output.
    No trust logic or default overrides live here.

    Three-state layer verdicts — derived purely from orchestrator output:

    Orchestrator B1-fatal path (orchestrator.py lines 384-448):
        mbd_dict  = None                                → MBD skip
        b2_dict   = {"status": "Skipped (B1 fatal)",   → B2 skip
                     "validation_valid": False, ...}
        cp_dict   = None                                → CP skip
        b3_result = {"available": False,                → B3 skip
                     "status": "skipped (B1 fatal)", ...}
        result also contains: "skipped_layers": ["MBD", "B2", "CP", "B3"]

    Normal path:
        mbd_dict  = dict (may be None if enable_mbd=False)
        b2_dict   = ExplainabilityReport.to_dict()
        cp_dict   = dict (may be None if enable_cp=False)
        b3_result = {"available": True/False, "label": ..., "status": "ok"/...}

    Layer state derivation rules:
        B1:  "flag" if b1["valid"] is False, else "pass"
        MBD: "skip" if r["mbd"] is None (B1-fatal or enable_mbd=False)
             "flag" if mbd["passed"] is False (kinematic/plausibility/replay anomaly detected)
             "pass" otherwise
        B2:  "skip" if b2.get("status") startswith "Skipped"
             "flag" if b2.get("validation_valid") is False (and not skipped)
             "pass" otherwise
        CP:  "skip" if r["cp"] is None (B1-fatal or enable_cp=False)
             "flag" if cp["observations_available"] is True AND cp["cp_pass"] is False
                     (genuine contradiction — reports actively disagree)
             "pass" otherwise (corroboration deficit → uncertainty, not a flag)
        B3:  "skip" if b3.get("status", "").lower() contains "skipped" or "disabled"
             "flag" if b3.get("available") and b3.get("label") != "BENIGN"
             "pass" otherwise
    """
    b1 = r.get("b1") or {}
    b2 = r.get("b2") or {}
    b3 = r.get("b3") or {}

    # decision: r["decision"] is already the trust_level value string
    decision_raw = r.get("decision", "CAUTION")
    if hasattr(decision_raw, "value"):
        decision_str = decision_raw.value.upper()
    else:
        decision_str = str(decision_raw).upper()
    if decision_str not in ("ACCEPT", "CAUTION", "REJECT"):
        decision_str = "CAUTION"

    sender = rec.get("sender", "unknown")
    x = rec.get("x", 0.0)
    y = rec.get("y", 0.0)
    speed = rec.get("speed", 0.0)

    # ── B1 ────────────────────────────────────────────────────────────────
    # valid=False iff fatal OR any reasons present (ValidationAssessment.valid
    # property: not self.fatal and len(self.reasons) == 0)
    b1_valid = b1.get("valid")
    b1_state = "flag" if b1_valid is False else "pass"

    # ── MBD ───────────────────────────────────────────────────────────────
    # Orchestrator sets mbd_dict = None on B1-fatal path (line 385) and
    # also when enable_mbd=False.
    # MBDResult.passed (mbd_layer.py line 378):
    #   passed = plausibility_pass and kinematics_ok and (replay_score < 0.9)
    # Both "passed" and "mbd_pass" are set to the same value in MBDResult.__init__.
    mbd_raw = r.get("mbd")
    if mbd_raw is None:
        mbd_state = "skip"
    elif mbd_raw.get("passed") is False:
        mbd_state = "flag"
    else:
        mbd_state = "pass"

    # ── B2 ────────────────────────────────────────────────────────────────
    # B1-fatal stub has status="Skipped (B1 fatal)" (orchestrator line 396).
    # Normal path sets status via ExplainabilityReport.to_dict().
    # validation_valid is B1's valid passthrough, then further modified by
    # the CP fold in orchestrator.py (lines 638-670).
    b2_status = str(b2.get("status", ""))
    if b2_status.startswith("Skipped"):
        b2_state = "skip"
    elif b2.get("validation_valid") is False:
        b2_state = "flag"
    else:
        b2_state = "pass"

    # ── CP ────────────────────────────────────────────────────────────────
    # Orchestrator sets cp_dict = None on B1-fatal path (line 400) and
    # when enable_cp=False.
    # Two distinct CP conditions (orchestrator.py lines 568-594):
    #   - CONTRADICTION: observations_available=True AND cp_pass=False
    #     → reports actively disagree on the shared claimed event → "flag"
    #   - CORROBORATION DEFICIT: observations_available=False or few/diverse
    #     → absence of evidence, not an attack → uncertainty via confidence,
    #     not a frame "flag" (stays "pass")
    # cp_pass is set by cp_layer.py line 165:
    #   cp_pass = bool(confidence > 0.7) if observations_available else True
    cp_raw = r.get("cp")
    if cp_raw is None:
        cp_state = "skip"
    elif cp_raw.get("observations_available") and not cp_raw.get("cp_pass"):
        cp_state = "flag"
    else:
        cp_state = "pass"

    # ── B3 ────────────────────────────────────────────────────────────────
    # B1-fatal stub: available=False, status="skipped (B1 fatal)" (line 407).
    # Ablation stub: status="disabled (ablation: enable_b3=False)" (line 503).
    # Normal unavailable: available=False, status varies.
    b3_status = str(b3.get("status", "")).lower()
    if "skipped" in b3_status or "disabled" in b3_status:
        b3_state = "skip"
    elif b3.get("available") and b3.get("label") != "BENIGN":
        b3_state = "flag"
    else:
        b3_state = "pass"

    lats = r.get("latencies") or {}

    return {
        "id": str(rec.get("id", sender)),
        "title": f"Injected: {sender}",
        "payload": rec.get("payload", ""),
        "meta": rec.get("meta_str", ""),
        "layers": {
            "B1":  b1_state,
            "MBD": mbd_state,
            "B2":  b2_state,
            "CP":  cp_state,
            "B3":  b3_state,
        },
        "decision": decision_str,
        "reason": r.get("reason", ""),
        "expected_label": rec.get("expected_label", "\u2014"),
        "latencies": {
            "PKI": round(lats.get("pki_ms") or 0.0, 2),
            "B1":  round(lats.get("b1_ms")  or 0.0, 2),
            "MBD": round(lats.get("mbd_ms") or 0.0, 2) if lats.get("mbd_ms") is not None else None,
            "B2":  round(lats.get("b2_ms")  or 0.0, 2) if lats.get("b2_ms")  is not None else None,
            "CP":  round(lats.get("cp_ms")  or 0.0, 2) if lats.get("cp_ms")  is not None else None,
            "B3":  round((lats.get("synthesizer_ms") or 0.0) + (lats.get("bridge_ms") or 0.0), 2) if lats.get("bridge_ms") is not None else None,
            "TE":  round(lats.get("fusion_ms") or 0.0, 2),
            "total_ms": round(lats.get("total_ms") or 0.0, 2),
        },
    }


# ---------------------------------------------------------------------------
# Inject-record → CAM message converter
#
# The parser in b1_scsv/models.py::safe_parse_cam() has a FLAT-DICT SHORTCUT
# (lines 392-409): when the dict has "x", "y", "sender" keys it bypasses
# the nested CAM structure and maps directly:
#
#   station_id  = int(raw["sender"])   ← ValueError if sender is non-numeric!
#   latitude    = float(raw["y"])      ← ETSI 1e-7-degree units (direct pass)
#   longitude   = float(raw["x"])      ← ETSI 1e-7-degree units (direct pass)
#   speed       = float(raw["speed"])  ← ETSI 0.01 m/s units (direct pass)
#   heading     = float(raw["heading"])← ETSI 0.1-degree units (direct pass)
#   station_type= 5 (hardcoded)
#   message_id  = 1 (hardcoded)
#   timestamp   = int(raw["timestamp"])
#
# We use this shortcut intentionally because it is fast and avoids duplicating
# the nested CAM builder. We just need to supply compatible values:
#
#   sender     → must be a numeric string (we hash non-numeric senders)
#   x, y       → treat as decimal degrees; multiply by 1e7 to get ETSI units
#                 (B1's coordinate range check uses ETSI units: ±900_000_000
#                 for lat, ±1_800_000_000 for lon; decimal degree inputs like
#                 51.5 would pass as-is because 51.5 << 900_000_000)
#   speed      → inject body is in m/s; ETSI unit is 0.01 m/s → multiply × 100
#   heading    → inject body is in degrees 0-360; ETSI unit is 0.1° → × 10
#   timestamp  → inject body is a Unix float; ETSI generation_delta_time is
#                millis mod 65536; store the Unix ms value so freshness check
#                (age = scenario_time_ms - cam.timestamp) works correctly.
#                The orchestrator derives scenario_time_ms from the largest
#                timestamp in the window, so using the same value for both
#                means age ≈ 0 and the freshness check passes for valid inputs.
#
# B1 will produce REALISTIC output for each inject:
#   - Well-formed numeric fields → B1 passes (no fatal, no penalties)
#   - Missing / zero speed or heading → still passes (None skips the check)
#   - Non-numeric sender → int() raises → safe_parse_cam returns cam=None → FATAL
#   - Timestamp=0 with current scenario_time_ms → stale by ~current_time → penalty
#
# We do NOT paper over missing fields: if the request omits them they stay as
# the default (0.0), and the pipeline sees what it sees.  The only translation
# we do is unit conversion (degrees→ETSI) and ensuring the sender is numeric.
# ---------------------------------------------------------------------------

def _sender_to_station_id(sender: str) -> str:
    """Return a stable numeric string for any sender value.

    safe_parse_cam() calls int(raw["sender"]); it will raise ValueError for
    non-numeric strings like "test" or "inject".  We convert by hashing to
    a positive 32-bit integer so the sender is always parseable.
    """
    try:
        int(sender)
        return sender  # already numeric, keep as-is
    except (ValueError, TypeError):
        # Stable hash: take abs() of Python hash, truncate to 8 decimal digits
        return str(abs(hash(sender)) % 100_000_000)


def _inject_record_to_cam(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a flat inject payload to the flat-dict CAM shape that
    safe_parse_cam()'s shortcut path (models.py:392-409) understands.

    Unit conversions (all derived from reading models.py):
        x_deg, y_deg  → kept as decimal degrees; the flat-dict shortcut stores
                         them as latitude/longitude directly.
        speed in/out in m/s (B1 shortcut path reads float(raw["speed"])).
        heading in/out in degrees.
        timestamp → Unix seconds × 1000 → millis.

    Synthesizer field paths (pipeline/synthesizer.py::_extract_cam_telemetry):
        station_type  ← cam.cam_parameters.basic_container.station_type
                        OR msg["station_type"]  (root fallback)
        yaw_rate      ← hfc["yaw_rate"]   — NO root fallback; must be in hfc
        long_accel    ← hfc["longitudinal_acceleration"]  — NO root fallback
        gen_dt        ← cam.generation_delta_time  → rendered as "timestamp="

    The free-text payload is surfaced to B3 via two channels:
        "event"      → synthesizer reads target_msg.get("event") as ego_event,
                       renders as "Ego vehicle reports: <text>"
        "scene_context.rsu_messages[].advisory"
                     → synthesizer renders as RSU advisory line
    Both channels survive the flat-dict shortcut because the shortcut does NOT
    strip unknown keys from the raw dict; the synthesizer reads them from raw.
    """
    payload_text = rec.get("payload", "")

    # Derive a numeric-safe station ID (int() in safe_parse_cam shortcut)
    sender_str = str(rec.get("sender", "inject"))
    numeric_sender = _sender_to_station_id(sender_str)

    # Coordinate convention: CARLA and the UI send x as longitude and y as latitude.
    # safe_parse_cam's flat-dict shortcut expects raw["y"] = latitude and raw["x"] = longitude.
    x_in = float(rec.get("x", 0.0))   # contains ETSI longitude
    y_in = float(rec.get("y", 0.0))   # contains ETSI latitude
    lat_deg = x_in * 1e-7 if abs(x_in) > 1000 else x_in   # decode latitude from y
    lon_deg = y_in * 1e-7 if abs(y_in) > 1000 else y_in   # decode longitude from x

    # If coordinates are outside valid ranges, leave as raw ETSI so B1 detects fatal errors
    lat_out = x_in if not (-90.0  <= lat_deg <=  90.0) else lat_deg
    lon_out = y_in if not (-180.0 <= lon_deg <= 180.0) else lon_deg

    rec["meta_str"] = f"lat={lat_out:.4f} lon={lon_out:.4f} spd={rec.get('speed', 0)}"

    # Convert speed from ETSI cm/s to m/s before putting it in the dict
    speed_etsi = float(rec.get("speed", 0.0))
    speed_ms = speed_etsi / 100.0 if speed_etsi > 100 else speed_etsi

    # Convert heading from ETSI 0.1° to degrees before putting it in the dict
    heading_etsi = float(rec.get("heading", 0.0))
    heading_deg = heading_etsi / 10.0 if heading_etsi > 360 else heading_etsi

    timestamp_s = float(rec.get("timestamp", time.time()))
    timestamp_ms = int(timestamp_s * 1000) if timestamp_s != 0 else int(time.time() * 1000)
    # ETSI generation_delta_time is millis mod 65536 (0..65535)
    gen_delta = timestamp_ms % 65536

    # Build the scene_context for RSU advisory channel
    scene_ctx: Dict[str, Any] = dict(rec.get("scene_context") or {})
    scene_ctx["context"] = "urban"  # Ensure meaningful context for B3
    if payload_text:
        rsu_msgs = list(scene_ctx.get("rsu_messages") or [])
        rsu_msgs.append({"advisory": payload_text, "text": payload_text})
        scene_ctx["rsu_messages"] = rsu_msgs

    # High-frequency container sub-dict.
    # The synthesizer reads yaw_rate and longitudinal_acceleration from:
    #   cam.cam_parameters.high_frequency_container
    #       .basic_vehicle_container_high_frequency
    # These two fields have NO root-level fallback in _extract_cam_telemetry,
    # so they MUST appear under the basic_vehicle_container_high_frequency key.
    hfc_dict: Dict[str, Any] = {
        "speed":                     speed_ms,
        "heading":                   heading_deg,
        "yaw_rate":                  0.0,   # deg/s; 0.0 = straight ahead
        "longitudinal_acceleration": 0.0,   # m/s²; 0.0 = no acceleration
        "lateral_acceleration":      0.0,   # m/s²
        "vertical_acceleration":     0.0,   # m/s²
    }

    # The flat dict: uses safe_parse_cam's shortcut (x+y+sender present).
    # All keys beyond the shortcut's required set are passed through to the
    # synthesizer which reads them from the raw dict.
    #
    # safe_parse_cam shortcut maps:  raw["y"] → latitude,  raw["x"] → longitude
    # So we assign:  "y" = lat_out,  "x" = lon_out
    return {
        # --- Keys consumed by safe_parse_cam flat-dict shortcut ---
        "sender":    numeric_sender,
        "x":         lon_out,      # safe_parse_cam reads x → longitude
        "y":         lat_out,      # safe_parse_cam reads y → latitude
        "latitude":  lat_out,      # root fallback used by synthesizer
        "longitude": lon_out,      # root fallback used by synthesizer
        "speed":     speed_ms,
        "heading":   heading_deg,
        "timestamp": timestamp_ms,
        # --- Root-level synthesizer fallbacks ---
        # station_type has a root fallback in _extract_cam_telemetry;
        # yaw_rate/accel do NOT, but present at root for transparency.
        "station_type":              5,    # ETSI passengerCar → _station_type_name(5) = "passengerCar"
        "yaw_rate":                  0.0,
        "longitudinal_acceleration": 0.0,
        "lateral_acceleration":      0.0,
        "vertical_acceleration":     0.0,
        # --- Keys consumed by synthesizer / orchestrator ---
        "header":        {"station_id": numeric_sender},
        "event":         payload_text or None,   # ego_event → "Ego vehicle reports: …"
        "scene_context": scene_ctx,              # rsu_messages advisory channel
        "context":       "urban",
        "cam": {
            "generation_delta_time": gen_delta,  # → synthesizer gen_dt / "timestamp=" field
            "cam_parameters": {
                "basic_container": {
                    "reference_position": {
                        "latitude":  lat_out,    # e.g. 48.62 ← from y_in
                        "longitude": lon_out,    # e.g. 11.37 ← from x_in
                    },
                    "station_type": 5,           # ETSI passengerCar
                },
                "high_frequency_container": {
                    # Primary path the synthesizer reads for yaw_rate / long_accel:
                    #   hfc = _nested_get(msg, "cam.cam_parameters
                    #          .high_frequency_container
                    #          .basic_vehicle_container_high_frequency")
                    "basic_vehicle_container_high_frequency": hfc_dict,
                    # Also keep flat copies so any consumer reading
                    # cam.cam_parameters.high_frequency_container.{speed,heading}
                    # directly still gets values.
                    "speed":   speed_ms,
                    "heading": heading_deg,
                },
            },
        },
    }


# ---------------------------------------------------------------------------
# Pydantic model for /inject body
# ---------------------------------------------------------------------------
class InjectRequest(BaseModel):
    sender: str = Field(default="inject")
    x: float = Field(default=0.0, description="Longitude in decimal degrees")
    y: float = Field(default=0.0, description="Latitude in decimal degrees")
    speed: float = Field(default=0.0, description="Speed in m/s")
    heading: float = Field(default=0.0, description="Heading in degrees [0, 360)")
    timestamp: float = Field(
        default_factory=time.time,
        description="Unix timestamp in seconds; 0 triggers a B1 stale-timestamp penalty",
    )
    payload: str = Field(default="", description="Free-text scene description / attack payload")
    scene_context: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    _clients.add(ws)
    log.info("WS client connected (total=%d)", len(_clients))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _clients.discard(ws)
        log.info("WS client disconnected (total=%d)", len(_clients))


# ---------------------------------------------------------------------------
# POST /inject
# ---------------------------------------------------------------------------
@app.post("/inject")
async def inject(req: InjectRequest) -> JSONResponse:
    if _pipeline is None:
        return JSONResponse(
            status_code=503,
            content={"error": "pipeline not available", "detail": _pipeline_error},
        )

    rec: Dict[str, Any] = req.model_dump()
    rec["id"] = str(uuid.uuid4())

    cam_msg = _inject_record_to_cam(rec)

    try:
        result = _pipeline.run(
            [cam_msg],
            context=rec["scene_context"].get("context"),
        )
    except Exception as exc:
        log.exception("Pipeline run failed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "pipeline run failed", "detail": str(exc)},
        )

    frame = _result_to_frame(rec, result)

    # ── Raw pipeline layer output log ─────────────────────────────────────
    # Printed immediately after every inject so you can compare what the
    # pipeline actually returned for each layer against what the frame says.
    b1_raw  = result.get("b1") or {}
    mbd_raw = result.get("mbd")  # None when skipped
    b2_raw  = result.get("b2") or {}
    cp_raw  = result.get("cp")   # None when skipped
    b3_raw  = result.get("b3") or {}
    log.info(
        "[RAW] sender=%s "
        "| B1: valid=%s fatal=%s score=%s reasons=%s "
        "| MBD: %s "
        "| B2: validation_valid=%s validation_score=%s confidence_calibration=%s "
        "| CP: %s "
        "| B3: available=%s label=%s confidence=%s risk_level=%s status=%s "
        "| FRAME: B1=%s MBD=%s B2=%s CP=%s B3=%s decision=%s",
        req.sender,
        b1_raw.get("valid"),
        b1_raw.get("fatal"),
        b1_raw.get("score"),
        b1_raw.get("reasons"),
        (
            f"passed={mbd_raw.get('passed')} anomaly_score={mbd_raw.get('anomaly_score')} "
            f"kinematic_score={mbd_raw.get('kinematic_score')} replay_score={mbd_raw.get('replay_score')} "
            f"sybil_score={mbd_raw.get('sybil_score')} evidence={mbd_raw.get('evidence')}"
            if mbd_raw is not None else "SKIPPED"
        ),
        b2_raw.get("validation_valid"),
        b2_raw.get("validation_score"),
        b2_raw.get("confidence_calibration"),
        (
            f"cp_pass={cp_raw.get('cp_pass')} observations_available={cp_raw.get('observations_available')} "
            f"cp_confidence={cp_raw.get('cp_confidence')} spatial={cp_raw.get('spatial_score')} "
            f"speed={cp_raw.get('speed_score')} heading={cp_raw.get('heading_score')} "
            f"diversity={cp_raw.get('diversity_score')} num_reports={cp_raw.get('num_reports')}"
            if cp_raw is not None else "SKIPPED"
        ),
        b3_raw.get("available"),
        b3_raw.get("label"),
        b3_raw.get("confidence"),
        b3_raw.get("risk_level"),
        b3_raw.get("status"),
        frame["layers"]["B1"],
        frame["layers"]["MBD"],
        frame["layers"]["B2"],
        frame["layers"]["CP"],
        frame["layers"]["B3"],
        frame["decision"],
    )

    await _broadcast(json.dumps(frame))
    return JSONResponse(content=frame)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "pipeline_ready": _pipeline is not None,
        "ws_clients": len(_clients),
    }


# ---------------------------------------------------------------------------
# Dev entrypoint (python serve.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "frontend.stbv_platform.bridge.serve:app",
        host="0.0.0.0",
        port=8200,
        reload=False,
        log_level="info",
    )
