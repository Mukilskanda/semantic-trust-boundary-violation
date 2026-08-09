#!/usr/bin/env bash
# STBV Console launcher (single-laptop). Serves the dashboard; optional CARLA bridge.
set -e
MODE="${1:-demo}"
PORT="${PORT:-3000}"
echo "STBV Console — mode=$MODE"
echo "Serving dashboard at http://localhost:$PORT"
echo "  (optional) start CARLA bridge:  python bridge/carla_bridge.py --ws-port 8200"
echo "  then uncomment connectLive('ws://localhost:8200') in web/index.html"
cd "$(dirname "$0")/web"
python3 -m http.server "$PORT"
