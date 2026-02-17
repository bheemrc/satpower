"""Tests for component compatibility validation."""

import pytest
import numpy as np

from satpower.validation._checks import validate_system, ValidationResult
from satpower.regulation._eps_board import EPSBoard
from satpower.battery._pack import BatteryPack
from satpower.solar._panel import SolarPanel


class TestValidationResult:
    def test_passed_when_no_errors(self):
        result = ValidationResult(passed=True, warnings=[], errors=[])
        assert result.passed

    def test_not_passed_with_errors(self):
        result = ValidationResult(passed=False, errors=["bad"])
        assert not result.passed


class TestValidateSystem:
    @pytest.fixture
    def gomspace_eps(self):
        return EPSBoard.from_datasheet("gomspace_p31u")

    @pytest.fixture
    def std_battery(self):
        return BatteryPack.from_cell("panasonic_ncr18650b", "2S2P")

    @pytest.fixture
    def std_panels(self):
        return SolarPanel.cubesat_body("3U", "azur_3g30c")

    def test_compatible_system_passes(self, gomspace_eps, std_battery, std_panels):
        result = validate_system(gomspace_eps, std_battery, std_panels)
        assert result.passed
        assert len(result.errors) == 0

    def test_battery_series_mismatch_error(self):
        """Battery with wrong series count should trigger error."""
        eps = EPSBoard.from_datasheet("gomspace_p31u")  # designed for 2S
        # 4S1P battery: 4 series exceeds EPS design of 2S
        battery = BatteryPack.from_cell("panasonic_ncr18650b", "4S1P")
        panels = SolarPanel.cubesat_body("3U", "azur_3g30c")
        result = validate_system(eps, battery, panels)
        assert not result.passed
        assert any("series" in e.lower() for e in result.errors)

    def test_too_many_panels_warning(self):
        """More panels than EPS inputs should trigger a warning."""
        eps = EPSBoard.from_datasheet("gomspace_p31u")  # 6 inputs
        battery = BatteryPack.from_cell("panasonic_ncr18650b", "2S2P")
        panels = SolarPanel.cubesat_with_wings(
            "3U", "azur_3g30c", wing_count=4
        )  # 6 body + 4 wings = 10
        result = validate_system(eps, battery, panels)
        assert any("solar inputs" in w.lower() for w in result.warnings)

    def test_high_load_power_warning(self):
        """Loads exceeding estimated generation should warn."""
        eps = EPSBoard.from_datasheet("endurosat_eps_i_plus")
        battery = BatteryPack.from_cell("panasonic_ncr18650b", "2S2P")
        panels = SolarPanel.cubesat_body("3U", "azur_3g30c")
        result = validate_system(eps, battery, panels, loads_peak_power=100.0)
        assert any("peak load" in w.lower() for w in result.warnings)

    def test_no_load_power_no_warning(self, gomspace_eps, std_battery, std_panels):
        """Without load power specified, no generation capacity warning."""
        result = validate_system(gomspace_eps, std_battery, std_panels)
        gen_warnings = [w for w in result.warnings if "peak load" in w.lower()]
        assert len(gen_warnings) == 0

    def test_4g32c_cell_voc_vs_gomspace(self):
        """4-junction cell with 3.48V Voc should work with GomSpace (6.5V max)."""
        eps = EPSBoard.from_datasheet("gomspace_p31u")
        battery = BatteryPack.from_cell("panasonic_ncr18650b", "2S2P")
        panels = SolarPanel.cubesat_body("3U", "azur_4g32c")
        result = validate_system(eps, battery, panels)
        # Voc 3.48V < 6.5V max, should pass
        assert result.passed

    def test_clydespace_with_6u_system(self):
        """Clyde Space EPS with 6U body + 4 wings."""
        eps = EPSBoard.from_datasheet("clydespace_3g_eps")  # 7 inputs
        battery = BatteryPack.from_cell("lg_mj1", "2S2P")
        panels = SolarPanel.cubesat_with_wings(
            "6U", "azur_3g30c", wing_count=4, exclude_faces=["-Z"]
        )  # 5 body + 4 wings = 9 panels
        result = validate_system(eps, battery, panels)
        # 9 panels > 7 inputs: should warn
        assert any("solar inputs" in w.lower() for w in result.warnings)
