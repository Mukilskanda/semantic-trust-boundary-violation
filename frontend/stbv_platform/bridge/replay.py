#!/usr/bin/env python3
"""
frontend/stbv_platform/bridge/replay.py
========================================
Replays scenarios/demo_scenarios.json over the WebSocket served by serve.py.

Each trace is converted to the WebSocket frame shape that the dashboard
understands and sent to ws://localhost:8200/ws with a configurable delay.

Usage (from repo root):
    python frontend/stbv_platform/bridge/replay.py
    python frontend/stbv_platform/bridge/replay.py --delay 3 --loop
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="[replay] %(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Path to the scenarios file — relative to this script's location
_SCENARIOS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "scenarios",
    "demo_scenarios.json",
)


def _scenario_to_frame(scenario: dict, index: int) -> dict:
    """
    Convert a demo_scenarios.json entry to the WebSocket frame shape the
    dashboard expects.  The JSON fields are read directly; no pipeline call
    is made (this is for offline replay).

    demo_scenarios.json shape (partial):
      {
        "attack_id": "benign_cam",
        "family": "Benign CAM",
        "expected_label": "BENIGN",
        "injected_payload": "...",
        "layers": [{"layer":"B1","passed":true}, ...],
        "final_decision": "ACCEPT",
        "reason": "..."
      }
    """
    layers_list = scenario.get("layers", [])
    # Build a {layer_name: pass|flag} map
    layers_map: dict = {}
    for entry in layers_list:
        name = entry.get("layer", "")
        passed = entry.get("passed", True)
        if name in ("B1", "B2", "B3"):
            layers_map[name] = "pass" if passed else "flag"
    # Defaults for any layer not listed
    for layer in ("B1", "B2", "B3"):
        layers_map.setdefault(layer, "pass")

    decision = str(scenario.get("final_decision", "CAUTION")).upper()
    # Normalise to accepted values
    if decision not in ("ACCEPT", "CAUTION", "REJECT"):
        decision = "CAUTION"

    payload_text = scenario.get("injected_payload", "")

    return {
        "id": scenario.get("attack_id", f"replay_{index}"),
        "title": scenario.get("family", f"Scenario {index + 1}"),
        "payload": str(payload_text)[:200],
        "meta": f"replay #{index + 1} — {scenario.get('subcategory', '')}",
        "layers": layers_map,
        "decision": decision,
        "reason": scenario.get("reason", ""),
        "expected_label": scenario.get("expected_label", "\u2014"),
    }


async def run_replay(ws_url: str, delay: float, loop: bool) -> None:
    try:
        import websockets  # type: ignore[import]
    except ImportError:
        log.error("websockets not installed — run: pip install websockets")
        sys.exit(1)

    # Load scenarios
    try:
        with open(_SCENARIOS_PATH, encoding="utf-8") as fh:
            scenarios: list = json.load(fh)
    except FileNotFoundError:
        log.error("Scenarios file not found: %s", _SCENARIOS_PATH)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        log.error("Failed to parse scenarios JSON: %s", exc)
        sys.exit(1)

    if not scenarios:
        log.warning("scenarios/demo_scenarios.json is empty — nothing to replay.")
        return

    log.info("Loaded %d scenario(s) from %s", len(scenarios), _SCENARIOS_PATH)

    iteration = 0
    while True:
        iteration += 1
        log.info("Connecting to %s (pass %d)…", ws_url, iteration)

        try:
            async with websockets.connect(ws_url) as ws:
                log.info("Connected.")
                for idx, scenario in enumerate(scenarios):
                    frame = _scenario_to_frame(scenario, idx)
                    msg = json.dumps(frame)
                    await ws.send(msg)
                    log.info(
                        "Sent frame %d/%d: id=%s decision=%s",
                        idx + 1,
                        len(scenarios),
                        frame["id"],
                        frame["decision"],
                    )
                    if idx < len(scenarios) - 1:
                        await asyncio.sleep(delay)

        except (ConnectionRefusedError, OSError) as exc:
            log.error("Cannot connect to %s: %s", ws_url, exc)
            log.info("Is serve.py running?  Retrying in 5 s…")
            await asyncio.sleep(5)
            continue  # retry connection
        except Exception as exc:
            log.error("WebSocket error: %s", exc)

        if not loop:
            break

        log.info("Loop enabled — replaying in %.1f s…", delay)
        await asyncio.sleep(delay)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Replay demo_scenarios.json over the STBV WebSocket server."
    )
    ap.add_argument(
        "--url",
        default="ws://localhost:8200/ws",
        help="WebSocket URL of serve.py (default: ws://localhost:8200/ws)",
    )
    ap.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds between frames (default: 2)",
    )
    ap.add_argument(
        "--loop",
        action="store_true",
        help="Replay indefinitely (Ctrl-C to stop)",
    )
    args = ap.parse_args()

    try:
        asyncio.run(run_replay(args.url, args.delay, args.loop))
    except KeyboardInterrupt:
        log.info("Replay stopped.")


if __name__ == "__main__":
    main()
