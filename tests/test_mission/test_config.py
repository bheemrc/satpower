"""Tests for mission YAML configuration parsing."""

import pytest
from pathlib import Path

from satpower.mission._config import MissionConfig, OrbitConfig, SolarConfig
from satpower.mission._builder import load_mission, build_simulation

_MISSIONS_DIR = Path(__file__).parent.parent.parent / "src" / "satpower" / "data" / "missions"


class TestMissionConfigParsing:
    def test_load_earth_observation(self):
        config = load_mission(_MISSIONS_DIR / "earth_observation_3u.yaml")
        assert config.name == "EarthMapper-1"
        assert config.orbit.altitude_km == 550
        assert config.orbit.inclination_deg == 97.6
        assert config.satellite.form_factor == "3U"
        assert config.satellite.eps_board == "gomspace_p31u"
        assert config.satellite.solar.cell == "azur_3g30c"
        assert len(config.loads) == 5

    def test_load_iot_comms(self):
        config = load_mission(_MISSIONS_DIR / "iot_comms_3u.yaml")
        assert config.name == "IoT-Relay-1"
        assert config.satellite.solar.deployed_wings is None

    def test_load_tech_demo(self):
        config = load_mission(_MISSIONS_DIR / "tech_demo_iss.yaml")
        assert config.orbit.altitude_km == 408
        assert config.orbit.inclination_deg == 51.6

    def test_load_ais_maritime(self):
        config = load_mission(_MISSIONS_DIR / "ais_maritime_3u.yaml")
        assert config.satellite.eps_board == "clydespace_3g_eps"
        assert config.satellite.solar.deployed_wings is not None
        assert config.satellite.solar.deployed_wings.count == 2

    def test_load_scientific_6u(self):
        config = load_mission(_MISSIONS_DIR / "scientific_6u.yaml")
        assert config.satellite.form_factor == "6U"
        assert config.satellite.solar.deployed_wings.count == 4

    def test_loads_have_correct_triggers(self):
        config = load_mission(_MISSIONS_DIR / "earth_observation_3u.yaml")
        triggers = {l.name: l.trigger for l in config.loads}
        assert triggers["obc"] == "always"
        assert triggers["camera"] == "sunlight"
        assert triggers["heater"] == "eclipse"

    def test_deployed_wings_config(self):
        config = load_mission(_MISSIONS_DIR / "earth_observation_3u.yaml")
        wings = config.satellite.solar.deployed_wings
        assert wings is not None
        assert wings.count == 2
        assert wings.area_m2 == 0.06

    def test_exclude_faces(self):
        config = load_mission(_MISSIONS_DIR / "earth_observation_3u.yaml")
        assert config.satellite.solar.exclude_faces == ["-Z"]

    def test_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_mission("/nonexistent/path.yaml")

    def test_simulation_config_defaults(self):
        config = load_mission(_MISSIONS_DIR / "earth_observation_3u.yaml")
        assert config.simulation.duration_orbits == 10.0
        assert config.simulation.initial_soc == 1.0


class TestBuildSimulation:
    def test_build_from_config(self):
        config = load_mission(_MISSIONS_DIR / "earth_observation_3u.yaml")
        sim = build_simulation(config)
        assert sim is not None

    def test_build_with_wings(self):
        config = load_mission(_MISSIONS_DIR / "earth_observation_3u.yaml")
        sim = build_simulation(config)
        # Should have 5 body panels (1 excluded) + 2 wings = 7
        assert len(sim._panels) == 7

    def test_build_body_only(self):
        config = load_mission(_MISSIONS_DIR / "iot_comms_3u.yaml")
        sim = build_simulation(config)
        # Should have 6 body panels, no wings
        assert len(sim._panels) == 6

    def test_build_with_eps_board(self):
        config = load_mission(_MISSIONS_DIR / "earth_observation_3u.yaml")
        sim = build_simulation(config)
        assert sim._eps_board is not None
        assert sim._bus.bus_voltage == 3.3
