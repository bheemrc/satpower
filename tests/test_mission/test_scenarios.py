"""Integration tests — all 5 mission presets run and produce reasonable results."""

import pytest
from pathlib import Path

from satpower.mission._builder import load_mission, build_simulation
from satpower.simulation._report import generate_power_budget
from satpower.loads._profile import LoadProfile
from satpower.battery._pack import BatteryPack

_MISSIONS_DIR = Path(__file__).parent.parent.parent / "src" / "satpower" / "data" / "missions"

MISSION_PRESETS = [
    "earth_observation_3u",
    "iot_comms_3u",
    "tech_demo_iss",
    "ais_maritime_3u",
    "scientific_6u",
]


class TestMissionScenarios:
    @pytest.mark.parametrize("mission_name", MISSION_PRESETS)
    def test_mission_runs_successfully(self, mission_name):
        config = load_mission(_MISSIONS_DIR / f"{mission_name}.yaml")
        sim = build_simulation(config)
        results = sim.run(
            duration_orbits=config.simulation.duration_orbits,
            dt_max=60,
        )
        assert len(results.time) > 10

    @pytest.mark.parametrize("mission_name", MISSION_PRESETS)
    def test_soc_stays_bounded(self, mission_name):
        config = load_mission(_MISSIONS_DIR / f"{mission_name}.yaml")
        sim = build_simulation(config)
        results = sim.run(duration_orbits=config.simulation.duration_orbits, dt_max=60)
        assert results.soc.min() >= 0.0
        assert results.soc.max() <= 1.0

    @pytest.mark.parametrize("mission_name", MISSION_PRESETS)
    def test_positive_power_margin(self, mission_name):
        config = load_mission(_MISSIONS_DIR / f"{mission_name}.yaml")
        sim = build_simulation(config)
        results = sim.run(duration_orbits=config.simulation.duration_orbits, dt_max=60)

        loads = LoadProfile()
        for load in config.loads:
            loads.add_mode(
                name=load.name,
                power_w=load.power_w,
                duty_cycle=load.duty_cycle,
                trigger=load.trigger,
            )
        battery = BatteryPack.from_cell(
            config.satellite.battery.cell,
            config.satellite.battery.config,
        )
        report = generate_power_budget(results, loads, battery, config.name)
        assert report.power_margin_w > 0, (
            f"{mission_name}: negative power margin {report.power_margin_w:.2f}W"
        )

    @pytest.mark.parametrize("mission_name", MISSION_PRESETS)
    def test_reasonable_dod(self, mission_name):
        config = load_mission(_MISSIONS_DIR / f"{mission_name}.yaml")
        sim = build_simulation(config)
        results = sim.run(duration_orbits=config.simulation.duration_orbits, dt_max=60)
        assert results.worst_case_dod < 0.50, (
            f"{mission_name}: DoD {results.worst_case_dod:.1%} exceeds 50%"
        )

    @pytest.mark.parametrize("mission_name", MISSION_PRESETS)
    def test_report_generation(self, mission_name):
        config = load_mission(_MISSIONS_DIR / f"{mission_name}.yaml")
        sim = build_simulation(config)
        results = sim.run(duration_orbits=config.simulation.duration_orbits, dt_max=60)

        loads = LoadProfile()
        for load in config.loads:
            loads.add_mode(
                name=load.name,
                power_w=load.power_w,
                duty_cycle=load.duty_cycle,
                trigger=load.trigger,
            )
        battery = BatteryPack.from_cell(
            config.satellite.battery.cell,
            config.satellite.battery.config,
        )
        report = generate_power_budget(results, loads, battery, config.name)

        # Report text should contain the mission name
        text = report.to_text()
        assert config.name in text
        assert "VERDICT" in text

        # Dict conversion should work
        d = report.to_dict()
        assert d["mission_name"] == config.name
        assert "avg_generated_w" in d
