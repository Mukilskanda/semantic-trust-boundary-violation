"""
deployment_eval/carla_bridge.py
================================
Converts LIVE CARLA vehicle state into this repository's native,
ETSI-style nested CAM/DENM message schema -- the exact schema consumed
by B1/SCSV (`b1_scsv/scsv.py`) and, downstream, by
`bridges/message_adapter.py::to_flat_report` (MBD/CP). This is the same
nested shape used throughout `test_messages/**/*.json` (see
`header.station_id`, `cam.cam_parameters.basic_container.reference_position`,
etc.) -- built here from CARLA's live `carla.Transform`/`carla.Vector3D`
instead of from a static fixture file.

CARLA gives Unreal Engine local Cartesian coordinates (meters, left-handed,
Z-up), NOT geodetic lat/lon. There is no live GPS signal to read. Rather
than silently inventing a bogus datum, this bridge anchors an arbitrary
but FIXED real-world reference point (`ORIGIN_LAT_DEG`/`ORIGIN_LON_DEG`)
and derives ETSI fixed-point lat/lon from CARLA's (x, y) via the exact
INVERSE of `bridges/message_adapter.py::project_to_local_meters` --
i.e. round-tripping through that adapter recovers the original CARLA
(x, y) to within equirectangular-projection error (<1% at these ranges,
per that module's own docstring). This is a disclosed, deliberate
approximation, not a bug: it is the standard technique for bridging a
Cartesian sim to a geodetic-coordinate pipeline when no real GNSS receiver
is present (documented explicitly in CARLA_DEPLOYMENT_EVALUATION.md).

Speed/heading unit conventions (ETSI CAM, matching
bridges/message_adapter.py's own decoding rules exactly):
  - speed: 0.01 m/s fixed-point integer (so 15.0 m/s -> 1500)
  - heading: 0.1 degree fixed-point integer, compass bearing 0-3600
    (0 = North, clockwise), derived from CARLA's UE4 yaw (0 = +X axis,
    clockwise from above) via heading = (90 - yaw) mod 360 -- CARLA's
    +X is UE4 "East" by convention in the standard town maps, so this
    matches compass bearing to the same approximation as the coordinate
    projection above.

Does NOT modify the pipeline, B1/MBD/B2/CP/B3, or the Trust Decision
Engine. This module only produces input messages in the pipeline's own
existing wire format.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import carla  # type: ignore

# Arbitrary but fixed real-world anchor point (central Germany), matching
# the same order of magnitude as this repo's existing fixed-point test
# fixtures (e.g. test_messages/benign/normal_car.json's 485512345 /
# 96123456) purely for continuity of "plausible ETSI CAM" values -- not
# claimed to be CARLA's actual real-world location (it has none).
ORIGIN_LAT_DEG = 48.5512345
ORIGIN_LON_DEG = 9.6123456
_EARTH_RADIUS_M = 6_371_000.0
_ORIGIN_LAT_RAD = math.radians(ORIGIN_LAT_DEG)
_ORIGIN_LON_RAD = math.radians(ORIGIN_LON_DEG)

# DENM cause codes, matching bridges/message_adapter.py::_extract_denm_event's
# _CAUSE_MAP exactly, so DENM messages built here decode to the same event
# labels the frozen pipeline already understands.
DENM_CAUSE_ACCIDENT = 2
DENM_CAUSE_ROAD_WORKS = 3
DENM_CAUSE_HAZARDOUS_LOCATION = 9
DENM_CAUSE_OBSTACLE_ON_ROAD = 97


def _local_meters_to_etsi_latlon(x_m: float, y_m: float) -> tuple[int, int]:
    """Inverse of bridges.message_adapter.project_to_local_meters: given
    CARLA (x, y) meters relative to the fixed ORIGIN above, returns
    (lat_fixed_point, lon_fixed_point) in ETSI's 1e-7-degree integer
    convention. CARLA's y-axis grows south in UE4's left-handed frame,
    so it is negated to match the adapter's y = north-positive convention
    before inversion -- documented here, not silently absorbed.
    """
    y_north_m = -y_m
    lat_rad = _ORIGIN_LAT_RAD + (y_north_m / _EARTH_RADIUS_M)
    lon_rad = _ORIGIN_LON_RAD + (x_m / (_EARTH_RADIUS_M * math.cos(_ORIGIN_LAT_RAD)))
    lat_fixed = int(round(math.degrees(lat_rad) * 1e7))
    lon_fixed = int(round(math.degrees(lon_rad) * 1e7))
    return lat_fixed, lon_fixed


def _carla_yaw_to_etsi_heading(yaw_deg: float) -> int:
    """CARLA yaw (UE4 convention, 0=+X axis, clockwise-positive when
    viewed from above) -> ETSI compass heading (0=North, clockwise),
    0.1-degree fixed point. See module docstring for the mapping used."""
    heading_deg = (90.0 - yaw_deg) % 360.0
    return int(round(heading_deg * 10.0))


@dataclass
class VehicleSnapshot:
    """One vehicle's live state at one CARLA tick, already extracted from
    the carla.Actor (kept separate from message construction so the same
    snapshot can be reused to build both a truthful CAM and, for attack
    scenarios, a deliberately falsified one)."""
    actor_id: int
    station_id: int
    station_type: int  # ETSI: 5=passengerCar, 8=heavyTruck, 2=cyclist, etc.
    x_m: float
    y_m: float
    speed_mps: float
    yaw_deg: float
    yaw_rate: float
    sim_time_s: float


def snapshot_vehicle(actor: "carla.Actor", station_id: int, station_type: int,
                      sim_time_s: float) -> VehicleSnapshot:
    tf = actor.get_transform()
    vel = actor.get_velocity()
    av = actor.get_angular_velocity()
    speed = math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2)
    return VehicleSnapshot(
        actor_id=actor.id,
        station_id=station_id,
        station_type=station_type,
        x_m=tf.location.x,
        y_m=tf.location.y,
        speed_mps=speed,
        yaw_deg=tf.rotation.yaw,
        yaw_rate=av.z,
        sim_time_s=sim_time_s,
    )


def build_cam_message(
    snap: VehicleSnapshot,
    message_id: int,
    certificate_id: Optional[str] = None,
    is_attacker: bool = False,
    event_override: Optional[str] = None,
    denm_cause_code: Optional[int] = None,
    lat_override: Optional[int] = None,
    lon_override: Optional[int] = None,
    speed_override_mps: Optional[float] = None,
    timestamp_override_ms: Optional[float] = None,
) -> Dict[str, Any]:
    """Builds one native-schema CAM (optionally +DENM) message from a live
    VehicleSnapshot. `*_override` parameters exist ONLY so attack
    scenarios (replay, Sybil, semantic manipulation, ...) can construct a
    message that deliberately diverges from the snapshot's true physical
    state -- every override is applied explicitly and is visible in the
    returned dict, never silently substituted.
    """
    lat_fixed, lon_fixed = _local_meters_to_etsi_latlon(snap.x_m, snap.y_m)
    if lat_override is not None:
        lat_fixed = lat_override
    if lon_override is not None:
        lon_fixed = lon_override

    speed_mps = speed_override_mps if speed_override_mps is not None else snap.speed_mps
    speed_fixed = int(round(speed_mps * 100.0))  # 0.01 m/s units
    heading_fixed = _carla_yaw_to_etsi_heading(snap.yaw_deg)
    timestamp_ms = timestamp_override_ms if timestamp_override_ms is not None else snap.sim_time_s * 1000.0

    msg: Dict[str, Any] = {
        "header": {"station_id": snap.station_id, "message_id": message_id},
        "cam": {
            "generation_delta_time": timestamp_ms,
            "cam_parameters": {
                "basic_container": {
                    "station_type": snap.station_type,
                    "reference_position": {"latitude": lat_fixed, "longitude": lon_fixed},
                },
                "high_frequency_container": {
                    "basic_vehicle_container_high_frequency": {
                        "speed": speed_fixed,
                        "heading": heading_fixed,
                        "yaw_rate": snap.yaw_rate,
                        "steering_wheel_angle": 0,
                        "lateral_acceleration": 0,
                        "longitudinal_acceleration": 0,
                    }
                },
            },
        },
        "certificate_id": certificate_id or f"CERT_CARLA_{snap.station_id}",
        "cert_id": certificate_id or f"CERT_CARLA_{snap.station_id}",
        "is_attacker": is_attacker,
        "timestamp": timestamp_ms,
        "source": "carla_live",
    }
    if event_override is not None:
        msg["event"] = event_override
    if denm_cause_code is not None:
        msg["message_type"] = "DENM"
        msg["denm"] = {
            "management": {"event_type": {"cause_code": denm_cause_code}},
            "situation": {"event_type": {"cause_code": denm_cause_code}},
        }
    return msg


@dataclass
class CarlaSession:
    """Owns the CARLA client/world connection, synchronous-mode ticking,
    and spawned-actor lifecycle for the whole evaluation run."""
    host: str = "127.0.0.1"
    port: int = 2000
    town: str = "Town01"
    fixed_delta_seconds: float = 0.1
    client: Any = field(default=None, init=False)
    world: Any = field(default=None, init=False)
    tm: Any = field(default=None, init=False)
    actors: List[Any] = field(default_factory=list, init=False)
    sim_time_s: float = field(default=0.0, init=False)
    _orig_settings: Any = field(default=None, init=False)

    def connect(self) -> None:
        self.client = carla.Client(self.host, self.port)
        self.client.set_timeout(60.0)
        self.world = self.client.get_world()
        if self.world.get_map().name.split("/")[-1] != self.town:
            self.world = self.client.load_world(self.town)
        self._orig_settings = self.world.get_settings()
        settings = self.world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = self.fixed_delta_seconds
        self.world.apply_settings(settings)
        self.tm = self.client.get_trafficmanager(8000)
        self.tm.set_synchronous_mode(True)
        self.tm.set_global_distance_to_leading_vehicle(2.0)

    def spawn_traffic(self, n_vehicles: int, autopilot: bool = True, seed: int = 0) -> List[Any]:
        import random
        rng = random.Random(seed)
        bp_lib = self.world.get_blueprint_library()
        vehicle_bps = list(bp_lib.filter("vehicle.*"))
        # Filter to 4-wheeled vehicles only (matches ETSI station_type=5
        # passengerCar/heavyTruck semantics used throughout this repo's
        # fixtures; two-wheelers use a different station_type and are not
        # needed for these scenarios).
        vehicle_bps = [bp for bp in vehicle_bps if int(bp.get_attribute("number_of_wheels")) == 4]
        spawn_points = self.world.get_map().get_spawn_points()
        rng.shuffle(spawn_points)
        spawned = []
        for i in range(min(n_vehicles, len(spawn_points))):
            bp = rng.choice(vehicle_bps)
            if bp.has_attribute("color"):
                colors = bp.get_attribute("color").recommended_values
                bp.set_attribute("color", rng.choice(colors))
            actor = self.world.try_spawn_actor(bp, spawn_points[i])
            if actor is None:
                continue
            if autopilot:
                actor.set_autopilot(True, self.tm.get_port())
            spawned.append(actor)
            self.actors.append(actor)
        self.world.tick()
        self.sim_time_s += self.fixed_delta_seconds
        return spawned

    def tick(self) -> float:
        self.world.tick()
        self.sim_time_s += self.fixed_delta_seconds
        return self.sim_time_s

    def get_spectator_camera_capture(self, out_path: str, actor_to_follow: Optional[Any] = None) -> None:
        """Positions the spectator above/behind a vehicle (or the map
        origin if none given) and saves one RGB frame -- used for the
        'CARLA scene' figure. Uses a temporary sensor.camera.rgb actor,
        destroyed immediately after one frame."""
        bp_lib = self.world.get_blueprint_library()
        cam_bp = bp_lib.find("sensor.camera.rgb")
        cam_bp.set_attribute("image_size_x", "1280")
        cam_bp.set_attribute("image_size_y", "720")
        cam_bp.set_attribute("fov", "90")
        if actor_to_follow is not None:
            tf = actor_to_follow.get_transform()
            loc = tf.location + carla.Location(x=-8, z=4) + carla.Location(
                x=-4 * math.cos(math.radians(tf.rotation.yaw)),
                y=-4 * math.sin(math.radians(tf.rotation.yaw)),
            )
            cam_transform = carla.Transform(
                loc + carla.Location(z=0),
                carla.Rotation(pitch=-15, yaw=tf.rotation.yaw),
            )
        else:
            cam_transform = carla.Transform(carla.Location(x=0, y=0, z=50), carla.Rotation(pitch=-90))
        cam = self.world.spawn_actor(cam_bp, cam_transform)
        captured = {}

        def _on_image(image):
            captured["image"] = image

        cam.listen(_on_image)
        for _ in range(5):
            self.world.tick()
        if "image" in captured:
            captured["image"].save_to_disk(out_path)
        cam.stop()
        cam.destroy()
        self.world.tick()

    def cleanup(self) -> None:
        for actor in self.actors:
            try:
                if actor.is_alive:
                    actor.destroy()
            except Exception:
                pass
        self.actors.clear()
        if self._orig_settings is not None and self.world is not None:
            self._orig_settings.synchronous_mode = False
            self.world.apply_settings(self._orig_settings)
        if self.tm is not None:
            try:
                self.tm.set_synchronous_mode(False)
            except Exception:
                pass
