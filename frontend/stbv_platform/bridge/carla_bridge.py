#!/usr/bin/env python3
"""
carla_bridge.py — CARLA -> STBV pipeline -> dashboard (WebSocket)
================================================================
Receives vehicle/world state from CARLA, converts it to CAM-shaped V2X
messages, runs them through the REAL STBV pipeline (B1 -> B2 -> B3 -> Decision),
and streams the per-layer verdict to the dashboard over WebSocket.

STATUS: integration stub. The pipeline call is real (imports your ISCEPipeline);
CARLA ingestion is marked TODO where you wire in your CARLA client. Nothing here
fabricates a verdict — every decision comes from running the pipeline.

Run (from stbv_engine repo root, with CARLA running):
    pip install websockets carla
    python bridge/carla_bridge.py --carla-host localhost --ws-port 8200
Then in the dashboard, uncomment connectLive('ws://localhost:8200').
"""
from __future__ import annotations
import argparse, asyncio, json, sys, time


def carla_to_cam(actor_snapshot):
    """Convert a CARLA actor snapshot to a CAM-shaped flat report.
    TODO: map your CARLA actor fields to these keys."""
    t = actor_snapshot.get_transform() if hasattr(actor_snapshot, "get_transform") else None
    v = actor_snapshot.get_velocity() if hasattr(actor_snapshot, "get_velocity") else None
    loc = getattr(t, "location", None)
    rot = getattr(t, "rotation", None)
    return {
        "sender": getattr(actor_snapshot, "id", "carla_actor"),
        "x": getattr(loc, "x", 0.0),
        "y": getattr(loc, "y", 0.0),
        "speed": ((getattr(v, "x", 0.0) ** 2 + getattr(v, "y", 0.0) ** 2) ** 0.5) if v else 0.0,
        "heading": getattr(rot, "yaw", 0.0),
        "timestamp": time.time(),          # wall-clock; MBD freshness expects this
        "scene_context": {"context": "urban"},
    }


def result_to_frame(rec, r):
    b3 = r.get("b3", {}) or {}
    b1 = r.get("b1", {}) or {}
    b2 = r.get("b2", {}) or {}
    return {
        "id": str(rec.get("sender")),
        "title": f"CARLA vehicle {rec.get('sender')}",
        "payload": (r.get("synthesized_message", {}) or {}).get("text", "")[:200],
        "meta": f"x={rec.get('x'):.1f} y={rec.get('y'):.1f} spd={rec.get('speed'):.1f}",
        "layers": {
            "B1": "flag" if b1.get("valid", b1.get("passed")) is False else "pass",
            "B2": "flag" if b2.get("validation_valid") is False else "pass",
            "B3": "flag" if (b3.get("available") and b3.get("label") != "BENIGN") else "pass",
        },
        "decision": r.get("decision", "?"),
        "reason": r.get("reason", ""),
        "expected_label": rec.get("expected_label", "\u2014"),
    }


async def serve(args):
    try:
        import websockets
    except ImportError:
        print("pip install websockets"); return
    try:
        sys.path.insert(0, ".")
        from pipeline.orchestrator import ISCEPipeline
        pipe = ISCEPipeline()
        print("[carla_bridge] pipeline loaded")
    except Exception as e:
        print(f"[warn] pipeline import failed ({e}); bridge will idle."); pipe = None

    clients = set()

    async def handler(ws):
        clients.add(ws)
        try:
            await ws.wait_closed()
        finally:
            clients.discard(ws)

    async def broadcast(msg):
        for ws in list(clients):
            try:
                await ws.send(msg)
            except Exception:
                clients.discard(ws)

    async def carla_loop():
        # TODO: connect to CARLA and stream real snapshots:
        #   import carla
        #   world = carla.Client(args.carla_host, args.carla_port).get_world()
        #   while True:
        #       snap = world.wait_for_tick()
        #       for actor in world.get_actors().filter('vehicle.*'):
        #           rec = carla_to_cam(actor)
        #           r = pipe.run([rec], context='urban') if pipe else {}
        #           await broadcast(json.dumps(result_to_frame(rec, r)))
        while True:
            await asyncio.sleep(1)  # placeholder until CARLA client wired in

    async with websockets.serve(handler, "0.0.0.0", args.ws_port):
        print(f"[carla_bridge] WebSocket on :{args.ws_port} — "
              f"dashboard: connectLive('ws://localhost:{args.ws_port}')")
        await carla_loop()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--carla-host", default="localhost")
    ap.add_argument("--carla-port", type=int, default=2000)
    ap.add_argument("--ws-port", type=int, default=8200)
    args = ap.parse_args()
    try:
        asyncio.run(serve(args))
    except KeyboardInterrupt:
        print("\n[carla_bridge] stopped")


if __name__ == "__main__":
    main()
