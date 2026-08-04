#!/usr/bin/env bash
# deployment_eval/drive_multirun.sh
# ==================================
# Robust driver for the 15-run (3 towns x 5 seeds) CARLA deployment study.
#
# WHY A FRESH SERVER PER RUN: driving all 15 runs through one long-lived
# CARLA process destabilises it -- after ~2 runs the traffic manager starts
# returning `rpc::timeout ... register_vehicle` and the server then dies,
# taking the remaining runs with it. Accumulated actor/TM state is the
# cause. Starting a clean server per (town, seed) costs ~40 s of load time
# per run and removes the failure mode entirely.
#
# run_carla_multirun.py skips any (town, seed) whose JSON already exists, so
# this loop is idempotent and safely resumable after an interruption.

set -u
CARLA_DIR="/c/Users/mukil/Downloads/CARLA_0.9.16"
PY="/c/Users/mukil/anaconda3/python.exe"
PROJ="/c/semantic-trust-boundary-violation/semantic-trust-boundary-violation"
LOG="$PROJ/deployment_eval/multirun_log.txt"

TOWNS=(Town01 Town02 Town05)
SEEDS=(1 2 3 4 5)

kill_carla() {
  taskkill //F //IM CarlaUE4-Win64-Shipping.exe >/dev/null 2>&1
  taskkill //F //IM CarlaUE4.exe >/dev/null 2>&1
  sleep 6
}

echo "=== multi-run driver started $(date) ===" | tee "$LOG"

for TOWN in "${TOWNS[@]}"; do
  for SEED in "${SEEDS[@]}"; do
    TAG="${TOWN}_seed${SEED}"
    if [ -f "$PROJ/deployment_eval/carla_multirun/run_${TAG}.json" ]; then
      echo "[skip] $TAG already complete" | tee -a "$LOG"
      continue
    fi

    echo "--- $TAG : starting fresh CARLA ---" | tee -a "$LOG"
    kill_carla
    ( cd "$CARLA_DIR" && nohup ./CarlaUE4.exe -RenderOffScreen -carla-server \
        -nosound -quality-level=Low -carla-rpc-port=2000 >/dev/null 2>&1 & )
    sleep 40

    ( cd "$PROJ" && "$PY" -u deployment_eval/run_carla_multirun.py \
        --towns "$TOWN" --seeds "$SEED" ) 2>&1 | grep -vE "^INFO:" | tee -a "$LOG"

    kill_carla
  done
done

echo "=== driver finished $(date) ===" | tee -a "$LOG"
ls "$PROJ/deployment_eval/carla_multirun/"run_*.json 2>/dev/null | wc -l \
  | xargs echo "runs on disk:" | tee -a "$LOG"
