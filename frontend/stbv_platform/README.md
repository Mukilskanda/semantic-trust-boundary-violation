# STBV Trust Instrumentation Console

A production-grade interactive demonstration platform for **Semantic Trust
Boundary Violations (STBV)** in AI-enabled V2X systems. Built for
single-laptop presentation with an optional live CARLA feed.

**Core trust model:** B1 (structural) -> B2 (behavioral) -> B3 (semantic) ->
Decision. The console visualizes a message flowing down this "trust spine",
with each layer illuminating as it evaluates and the decision terminal
resolving to ACCEPT / CAUTION / REJECT.

---

## What ships

```
stbv_platform/
  web/index.html            self-contained dashboard (no build, no deps)
  bridge/carla_bridge.py    CARLA -> real pipeline -> WebSocket stub
  scenarios/demo_scenarios.json   sample scenarios (loadTraces schema)
  launch.sh                 one-command local server
  docs/                     this spec set
  README.md
```

The dashboard is a single HTML file: open it directly, or serve it with
`launch.sh`. It runs immediately with labelled **sample** scenarios (amber
banner). Replace them with real data two ways:

1. **Recorded traces** — call `loadTraces(<array>)` in the console with the
   output of `generate_decision_traces.py --format json`.
2. **Live CARLA** — run the bridge, then uncomment
   `connectLive('ws://localhost:8200')` at the bottom of `web/index.html`.

---

## Run — single laptop

```bash
# simplest: just open web/index.html in a browser
# or serve it:
./launch.sh                      # http://localhost:3000
```

Presentation tips:
- Click **⤢ Fullscreen** (top-right) for projector mode.
- Pick a scenario on the left; press **Run**, or **Step** through layer by layer.
- **Speed –/+** slows the animation for explanation; **Reset** replays.

## Run — with live CARLA

```bash
# terminal 1 (from your stbv_engine repo root, CARLA running):
pip install websockets carla
python bridge/carla_bridge.py --ws-port 8200

# terminal 2: serve the dashboard
./launch.sh
```
Then edit `web/index.html`, uncomment:
```js
connectLive('ws://localhost:8200');
```
The source badge turns green ("CARLA LIVE") when connected; if the bridge drops,
it falls back to replay automatically.

> The bridge's pipeline call is real — verdicts come from running B1/B2/B3.
> The CARLA ingestion loop is a marked TODO: wire your CARLA client into
> `carla_loop()` (the mapping helper `carla_to_cam()` is provided).

---

## Conference demo checklist

- [ ] Open fullscreen; confirm readable from the back of the room.
- [ ] Rehearse the scenario order: Benign -> Kinematic -> **Flagship STBV** ->
      Collusion -> Paraphrase (honest miss).
- [ ] Have replay-only mode ready as the zero-dependency fallback (works with
      no CARLA, no network).
- [ ] Pre-flight: load the page once, run each scenario once before the talk.
- [ ] Keep the amber "sample" banner OFF for the real demo by loading real
      traces or the live bridge.

---

## Design notes

Instrument-panel aesthetic: deep instrument-black base, teal "live signal"
accent for trust in motion, red for a semantic breach. Type pairs Space Grotesk
(display) with IBM Plex Mono (telemetry). The signature element is the **trust
spine** — the vertical rail with a pulse that travels through B1 -> B2 -> B3 as
each layer evaluates, so the pipeline reads as live instrumentation rather than
a static diagram. Respects reduced-motion and keyboard focus.

---


## New in this build

- **Expandable layers** — click any stage (PKI, B1, MBD, B2, CP, B3, Trust
  Engine) to reveal what it does and its per-check results (pass/fail) for the
  current message. PKI shows certificate-chain / ECDSA / validity / revocation;
  B1 shows ASN.1 schema / field ranges / freshness / replay; MBD shows kinematic
  bounds and Sybil score; and so on.
- **Standard ETSI message format** — sample cases are real ETSI CAM
  (EN 302 637-2) and DENM (EN 302 637-3) structures with IEEE 1609.2 security
  fields. Click **▸ raw** on the message bar to see the full ITS PDU
  (itsPduHeader, camParameters / denm containers, securedMessage).
- **Nine demonstration cases** — one benign, and one rejected at each of PKI /
  B1 / MBD / B2 / CP, plus the flagship STBV, colluding-peer, and paraphrase
  cases — so every layer is shown doing its job.

## Honest status

- The **dashboard** is complete and production-grade for presentation.
- The **pipeline** it visualizes is your real B1/B2/B3/Decision stack.
- The **CARLA bridge** is a working WebSocket server + real pipeline call with
  the CARLA ingestion loop left as a documented TODO — it will not invent
  vehicle data; you connect your CARLA client where marked.
- Sample scenarios are clearly labelled; do not present them as measured runs.
