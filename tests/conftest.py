"""Shared test fixtures for satpower."""

import pytest
import numpy as np

from satpower.orbit._propagator import Orbit
from satpower.orbit._eclipse import EclipseModel
from satpower.orbit._environment import OrbitalEnvironment
from satpower.solar._cell import SolarCell
from satpower.solar._panel import SolarPanel
from satpower.battery._cell import BatteryCell
from satpower.battery._pack import BatteryPack
from satpower.loads._profile import LoadProfile


@pytest.fixture
def iss_orbit():
    """ISS-like orbit: 408 km, 51.6° inclination."""
    return Orbit.circular(altitude_km=408, inclination_deg=51.6)


@pytest.fixture
def sso_orbit():
    """Sun-synchronous orbit: 550 km, 97.6° inclination."""
    return Orbit.circular(altitude_km=550, inclination_deg=97.6)


@pytest.fixture
def eclipse_model():
    return EclipseModel()


@pytest.fixture
def environment():
    return OrbitalEnvironment()


@pytest.fixture
def azur_cell():
    return SolarCell.from_datasheet("azur_3g30c")


@pytest.fixture
def panels_3u():
    return SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")


@pytest.fixture
def ncr18650b():
    return BatteryCell.from_datasheet("panasonic_ncr18650b")


@pytest.fixture
def battery_2s2p():
    return BatteryPack.from_cell("panasonic_ncr18650b", config="2S2P")


@pytest.fixture
def basic_loads():
    loads = LoadProfile()
    loads.add_mode("idle", power_w=2.0)
    loads.add_mode("comms", power_w=8.0, duty_cycle=0.15)
    loads.add_mode("payload", power_w=5.0, duty_cycle=0.30)
    return loads
