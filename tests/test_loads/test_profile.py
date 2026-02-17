"""Tests for load profile and duty cycling."""

import pytest

from satpower.loads._profile import LoadProfile


class TestLoadProfile:
    def test_add_mode(self):
        loads = LoadProfile()
        loads.add_mode("idle", power_w=2.0)
        assert len(loads.modes) == 1
        assert loads.modes[0].name == "idle"

    def test_invalid_duty_cycle(self):
        loads = LoadProfile()
        with pytest.raises(ValueError):
            loads.add_mode("bad", power_w=1.0, duty_cycle=1.5)

    def test_power_at_with_duty_cycle(self):
        loads = LoadProfile()
        loads.add_mode("idle", power_w=2.0, duty_cycle=1.0)
        loads.add_mode("comms", power_w=10.0, duty_cycle=0.5)
        # idle: 2W * 1.0 = 2W, comms: 10W * 0.5 = 5W => total = 7W
        assert abs(loads.power_at(0) - 7.0) < 0.01

    def test_trigger_sunlight_only(self):
        loads = LoadProfile()
        loads.add_mode("payload", power_w=5.0, trigger="sunlight")
        # In sunlight
        assert abs(loads.power_at(0, in_eclipse=False) - 5.0) < 0.01
        # In eclipse
        assert abs(loads.power_at(0, in_eclipse=True) - 0.0) < 0.01

    def test_trigger_eclipse_only(self):
        loads = LoadProfile()
        loads.add_mode("heater", power_w=3.0, trigger="eclipse")
        assert abs(loads.power_at(0, in_eclipse=True) - 3.0) < 0.01
        assert abs(loads.power_at(0, in_eclipse=False) - 0.0) < 0.01

    def test_active_modes(self, basic_loads):
        modes = basic_loads.active_modes(0, in_eclipse=False)
        assert "idle" in modes
        assert "comms" in modes

    def test_orbit_average_power(self):
        loads = LoadProfile()
        loads.add_mode("idle", power_w=2.0)
        loads.add_mode("payload", power_w=5.0, duty_cycle=0.3, trigger="sunlight")
        avg = loads.orbit_average_power(eclipse_fraction=0.35)
        # idle: 2W always, payload: 5*0.3*0.65 = 0.975W
        expected = 2.0 + 5.0 * 0.3 * 0.65
        assert abs(avg - expected) < 0.01
