# STBV Trust Pipeline — Deployment & Demo Specification

**Status of this document.** This is an engineering *specification and runbook*,
not a description of already-working infrastructure. The single-laptop launcher,
three-laptop distributed mode, CARLA/SUMO bridges, and WebSocket coordination
described here are **to be implemented** against the existing trust pipeline.
Items already present in the repository are marked **[EXISTS]**; everything else
is **[TO BUILD]**. Do not present unbuilt components as functional in the demo.

**Core trust model (unchanged).** The three trust layers are **B1 (structural)
→ B2 (behavioral) → B3 (semantic)**, followed by the **Decision** layer
(evidence fusion → ACCEPT / CAUTION / REJECT). The longer chain shown in demo
visualizations (PKI → B1 → MBD → B2 → CP → B3 → Trust Engine → Decision) is a
*presentation view* that surfaces auxiliary checks around the three core layers;
PKI/MBD/CP are supporting stages, not additional trust layers.

---

## 1. Overview

The same codebase supports three run modes from one configuration switch:

| Mode | Machines | Purpose |
|---|---|---|
| **Single-laptop** | 1 | Development, offline demo, JSON replay |
| **Three-laptop** | 3 | Full simulation: dashboard + CARLA + SUMO |
| **Conference demo** | 1 or 3 | Polished, projector-friendly presentation |

A single `MODE` setting (env var or `config/deploy.yaml`) selects the mode; no
code changes are required to switch. When only one machine is available, all
services fall back to `localhost`.

---

## 2. Single-Laptop Mode

### 2.1 Requirements
- One-click launch (single script).
- Backend, frontend, message broker, and trust pipeline all on `localhost`.
- CARLA and SUMO optional; if absent, replay scenarios from JSON.
- Manual message injection from the dashboard.

### 2.2 Services (all local)
| Service | Port (default) | Status |
|---|---|---|
| Trust pipeline (B1→B2→B3→Decision) | in-process / :8100 | **[EXISTS]** core; **[TO BUILD]** service wrapper |
| FastAPI backend | :8000 | **[TO BUILD]** |
| Next.js frontend / dashboard | :3000 | **[TO BUILD]** |
| Message broker (Redis or MQTT) | :6379 / :1883 | **[TO BUILD]** |
| CARLA (optional) | :2000 | external, **[TO BUILD]** bridge |
| SUMO/TraCI (optional) | :8813 | external, **[TO BUILD]** bridge |

### 2.3 One-click launch (target behavior)
```bash
./launch.sh --mode single          # everything on localhost
./launch.sh --mode single --no-sim # force JSON replay (skip CARLA/SUMO)
```
`launch.sh` should:
1. read `config/deploy.yaml`,
2. start the broker, then backend, then pipeline, then frontend,
3. probe for CARLA (:2000) and SUMO (:8813); if not reachable, set
   `SIM_SOURCE=replay` automatically (graceful fallback),
4. open the dashboard at `http://localhost:3000`.

### 2.4 JSON replay
- Replay a recorded/scripted scenario without any simulator.
- Source: `scenarios/*.json` (CAM/DENM-shaped messages + injected attacks).
- The existing corpus generator can export replay files
  (`export_semantic_split.py`, `generate_decision_traces.py`). **[EXISTS]**

### 2.5 Manual message injection
- Dashboard form → backend `/inject` → pipeline → live decision.
- Fields: sender id, kinematics (x,y,speed,heading), payload/scene text,
  optional attack template. **[TO BUILD UI]**; pipeline accepts single messages
  already **[EXISTS]**.

---

## 3. Three-Laptop (Distributed) Mode

The dashboard machine is the **central coordinator**, holding WebSocket
connections to the two simulation machines. Same codebase, `MODE=distributed`.

### 3.1 Laptop 1 — Presentation Dashboard (coordinator)
- Next.js frontend **[TO BUILD]**
- FastAPI backend **[TO BUILD]**
- Trust pipeline: PKI → B1 → MBD → B2 → CP → B3 → Trust Engine → Decision **[EXISTS core B1/B2/B3/Decision]**
- Manual message injection **[TO BUILD UI]**
- JSON replay **[EXISTS data path]**
- Live analytics + all visualizations **[TO BUILD]**
- WebSocket server for laptops 2 & 3 **[TO BUILD]**

### 3.2 Laptop 2 — CARLA
- CARLA simulator **[external]**
- ROS bridge (if used) **[TO BUILD/optional]**
- Vehicle state publisher → WebSocket → Laptop 1 **[TO BUILD]**
- Scenario controller **[TO BUILD]**
- Camera feeds (optional, bandwidth-heavy) **[TO BUILD]**
- World-state streaming **[TO BUILD]**

### 3.3 Laptop 3 — SUMO
- SUMO **[external]**
- TraCI controller **[TO BUILD]**
- Traffic generation **[TO BUILD]**
- RSUs + CAM/DENM message generation **[TO BUILD]**
- Traffic-density control **[TO BUILD]**

### 3.4 Network topology
```
        ┌─────────────────────────────┐
        │  Laptop 1  (Coordinator)    │
        │  Dashboard + Backend +      │
        │  Trust Pipeline + Analytics │
        │        WebSocket server     │
        └───────▲───────────▲─────────┘
                │           │
     WebSocket  │           │  WebSocket
                │           │
   ┌────────────┴───┐   ┌───┴────────────┐
   │ Laptop 2 CARLA │   │ Laptop 3 SUMO  │
   │ world + vehicle│   │ traffic + RSU  │
   │ state stream   │   │ CAM/DENM gen   │
   └────────────────┘   └────────────────┘
```
- Transport: WebSocket (JSON frames) over the LAN. **[TO BUILD]**
- Message schema: shared `contracts/` definitions so all three machines agree
  on CAM/DENM/attack payloads. **[EXISTS contracts for pipeline I/O]**
- Config: each machine reads the same `deploy.yaml`; `ROLE` selects which
  services start (`coordinator` | `carla` | `sumo`).

### 3.5 Launch (distributed)
```bash
# Laptop 1
./launch.sh --mode distributed --role coordinator --bind 0.0.0.0:8000
# Laptop 2
./launch.sh --mode distributed --role carla --coordinator ws://LAPTOP1_IP:8000
# Laptop 3
./launch.sh --mode distributed --role sumo  --coordinator ws://LAPTOP1_IP:8000
```
- If a sim laptop is unreachable, the coordinator falls back to JSON replay for
  that source and shows a "SIM OFFLINE — replay" badge (graceful fallback).

### 3.6 Single-laptop fallback
`MODE=distributed` with no remote roles started → all three roles run locally on
`localhost`, identical behavior. One codebase, no branching logic in the app.

---

## 4. Conference Demo Mode

`MODE=demo` (layers on top of single or distributed).

### 4.1 Requirements
- **One-click demo launch:** `./launch.sh --mode demo` starts everything and
  auto-opens the dashboard fullscreen.
- **Auto-load predefined attack scenarios:** curated set in
  `scenarios/demo/*.json` (e.g. the flagship collusion STBV, a benign control,
  a paraphrase-evasion case). Loaded in a fixed, rehearsed order.
- **Smooth animations, no debug output:** log level forced to `WARNING`; console
  hidden; message flow animated card-by-card through B1 → B2 → B3 → Decision.
- **Playback controls:** pause, replay, slow-motion, and single-step through
  message processing. Backend exposes `/demo/{play,pause,step,speed,reset}`.
  **[TO BUILD]**
- **Large-screen / projector UI:** high-contrast theme, large fonts, minimal
  chrome, 16:9 layout, readable from the back of a room. **[TO BUILD]**
- **Graceful fallback:** if CARLA/SUMO not running, demo silently uses JSON
  replay; no error dialogs on screen.
- **Auto-sync:** coordinator timestamps each step and broadcasts to sim machines
  so dashboard animation and simulator state stay aligned. **[TO BUILD]**

### 4.2 Recommended demo script (rehearsed flow)
1. Benign CAM → all layers green → ACCEPT (establish baseline).
2. Kinematic attack → B1/B2 flag → REJECT (show conventional defense works).
3. **Flagship STBV** → B1 green, B2 green, **B3 red** → REJECT
   (the money shot: authenticated + plausible, caught only by semantics).
4. Colluding-peers STBV → CP corroboration passes, B3 still catches → REJECT.
5. Paraphrase-evasion case → show a *miss* honestly, then explain the
   verbosity/dilution limitation (candor reads well to an academic audience).

### 4.3 Demo safety rails
- Pre-flight check script verifies all services up before the talk.
- "Reset" returns to slide 1 instantly.
- All scenarios are local JSON → demo works with **zero** network/simulator
  dependency if needed.

---

## 5. Configuration

`config/deploy.yaml` (single source of truth):
```yaml
mode: single            # single | distributed | demo
role: coordinator       # coordinator | carla | sumo   (distributed only)
sim_source: auto        # auto | carla | sumo | replay
broker: redis           # redis | mqtt
coordinator_url: ws://localhost:8000
replay_dir: scenarios/
demo:
  scenario_dir: scenarios/demo/
  fullscreen: true
  log_level: WARNING
  animation_speed: 1.0
ports:
  backend: 8000
  frontend: 3000
  pipeline: 8100
  broker: 6379
```

---

## 6. Build Checklist (what actually needs writing)

Ordered by dependency:

1. **[TO BUILD]** `launch.sh` orchestrator + `config/deploy.yaml` loader.
2. **[TO BUILD]** FastAPI backend wrapping the existing pipeline
   (`/inject`, `/replay`, `/stream`, `/demo/*`, `/health`).
3. **[TO BUILD]** Message broker integration (Redis pub/sub or MQTT).
4. **[TO BUILD]** Next.js dashboard: pipeline visualization (reuse the existing
   `stbv_decision_explorer.html` layer-card design as the component blueprint),
   analytics panels, injection form, playback controls.
5. **[TO BUILD]** WebSocket coordinator + sim-machine clients.
6. **[TO BUILD]** CARLA bridge (vehicle/world state → CAM-shaped messages).
7. **[TO BUILD]** SUMO/TraCI bridge (traffic + RSU → CAM/DENM).
8. **[TO BUILD]** Demo mode: fullscreen theme, scenario autoloader, sync clock.
9. **[EXISTS, reuse]** trust pipeline, corpus/scenario generators, decision-trace
   exporter, the decision-explorer UI as a design reference.

---

## 7. How to Run (quick reference)

```bash
# --- Single laptop, offline (safest for a talk) ---
./launch.sh --mode demo --no-sim
# opens fullscreen dashboard, loads scenarios/demo/*.json

# --- Single laptop, with simulators if present ---
./launch.sh --mode single

# --- Three laptops ---
# L1: ./launch.sh --mode distributed --role coordinator --bind 0.0.0.0:8000
# L2: ./launch.sh --mode distributed --role carla --coordinator ws://L1_IP:8000
# L3: ./launch.sh --mode distributed --role sumo  --coordinator ws://L1_IP:8000

# --- Health check before a demo ---
./launch.sh --preflight
```

---

## 8. Reality Check (do before relying on this)

- None of the `[TO BUILD]` items exist yet; budget real implementation time.
- The trust pipeline itself is the part that works; the demo is a presentation
  layer around it. Prioritize the **single-laptop demo mode with JSON replay** —
  it needs no CARLA/SUMO and covers 90% of a conference presentation with the
  least that can go wrong on stage.
- Three-laptop mode is impressive but adds network, sync, and two simulators as
  failure points. Have the single-laptop replay path as an always-ready fallback.
