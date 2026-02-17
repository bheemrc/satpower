"""Tests for mode scheduler."""

import pytest

from satpower.loads._profile import LoadProfile
from satpower.loads._scheduler import ModeScheduler


class TestModeScheduler:
    def test_passthrough_power(self):
        profile = LoadProfile()
        profile.add_mode("idle", power_w=2.0)
        sched = ModeScheduler(profile)
        assert abs(sched.power_at(0) - 2.0) < 0.01

    def test_passthrough_modes(self):
        profile = LoadProfile()
        profile.add_mode("idle", power_w=2.0)
        sched = ModeScheduler(profile)
        assert "idle" in sched.active_modes(0)
