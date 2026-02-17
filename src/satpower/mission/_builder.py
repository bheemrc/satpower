"""Build a Simulation from a mission YAML config."""

from __future__ import annotations

from pathlib import Path

import yaml

from satpower.mission._config import MissionConfig
from satpower.orbit._propagator import Orbit
from satpower.solar._panel import SolarPanel
from satpower.battery._pack import BatteryPack
from satpower.loads._profile import LoadProfile
from satpower.regulation._eps_board import EPSBoard
from satpower.simulation._engine import Simulation


def load_mission(path: str | Path) -> MissionConfig:
    """Load a mission configuration from a YAML file.

    Looks up bundled missions if the path doesn't exist as a file.
    """
    p = Path(path)
    if not p.exists():
        # Try bundled missions
        bundled = Path(__file__).parent.parent / "data" / "missions" / p.name
        if not bundled.suffix:
            bundled = bundled.with_suffix(".yaml")
        if bundled.exists():
            p = bundled
        else:
            raise FileNotFoundError(f"Mission file not found: {path}")

    with open(p) as f:
        data = yaml.safe_load(f)

    # Merge satellite.loads into top-level loads if top-level is empty
    sat = data.get("satellite", {})
    if "loads" in sat and not data.get("loads"):
        data["loads"] = sat.pop("loads")
    elif "loads" in sat:
        sat.pop("loads", None)

    return MissionConfig(**data)


def build_simulation(config: MissionConfig) -> Simulation:
    """Construct a Simulation from a MissionConfig."""
    # Orbit
    orbit = Orbit.circular(
        altitude_km=config.orbit.altitude_km,
        inclination_deg=config.orbit.inclination_deg,
        raan_deg=config.orbit.raan_deg,
    )

    # Solar panels
    sc = config.satellite.solar
    if sc.deployed_wings is not None:
        panels = SolarPanel.cubesat_with_wings(
            form_factor=config.satellite.form_factor,
            cell_type=sc.cell,
            wing_count=sc.deployed_wings.count,
            wing_area_m2=sc.deployed_wings.area_m2,
            exclude_faces=sc.exclude_faces if sc.body_panels else list(
                f"{s}{a}" for s in "+-" for a in "XYZ"
            ),
        )
    elif sc.body_panels:
        panels = SolarPanel.cubesat_body(
            form_factor=config.satellite.form_factor,
            cell_type=sc.cell,
            exclude_faces=sc.exclude_faces,
        )
    else:
        panels = []

    # Battery
    battery = BatteryPack.from_cell(
        config.satellite.battery.cell,
        config.satellite.battery.config,
    )

    # Loads
    loads = LoadProfile()
    for load in config.loads:
        loads.add_mode(
            name=load.name,
            power_w=load.power_w,
            duty_cycle=load.duty_cycle,
            trigger=load.trigger,
        )

    # EPS board (optional)
    eps_board = None
    if config.satellite.eps_board:
        eps_board = EPSBoard.from_datasheet(config.satellite.eps_board)

    return Simulation(
        orbit=orbit,
        panels=panels,
        battery=battery,
        loads=loads,
        initial_soc=config.simulation.initial_soc,
        eps_board=eps_board,
    )
