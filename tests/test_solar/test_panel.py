"""Tests for solar panel geometry."""

import numpy as np
import pytest

from satpower.solar._panel import SolarPanel


class TestCubesatBody:
    def test_3u_returns_6_panels(self):
        panels = SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")
        assert len(panels) == 6

    def test_1u_returns_6_panels(self):
        panels = SolarPanel.cubesat_body("1U", cell_type="azur_3g30c")
        assert len(panels) == 6

    def test_unknown_form_factor_raises(self):
        with pytest.raises(ValueError):
            SolarPanel.cubesat_body("10U", cell_type="azur_3g30c")

    def test_panel_normals_are_unit_vectors(self):
        panels = SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")
        for panel in panels:
            assert abs(np.linalg.norm(panel.normal) - 1.0) < 1e-10

    def test_3u_long_faces_larger_than_short(self):
        panels = SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")
        areas = {p.name: p.area_m2 for p in panels}
        # ±X, ±Z faces are 30x10 cm, ±Y faces are 10x10 cm
        assert areas["3U_+X"] > areas["3U_+Y"]


class TestPanelPower:
    def test_sun_facing_panel_generates_power(self):
        panels = SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")
        # +X panel with Sun along +X
        px_panel = [p for p in panels if "+X" in p.name][0]
        power = px_panel.power(
            sun_direction=np.array([1.0, 0.0, 0.0]),
            irradiance=1361.0,
            temperature_k=301.15,
        )
        assert power > 0

    def test_away_facing_panel_zero_power(self):
        panels = SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")
        px_panel = [p for p in panels if "+X" in p.name][0]
        # Sun along -X (behind panel)
        power = px_panel.power(
            sun_direction=np.array([-1.0, 0.0, 0.0]),
            irradiance=1361.0,
            temperature_k=301.15,
        )
        assert power == 0.0

    def test_total_power_positive(self, panels_3u):
        sun_dir = np.array([1.0, 0.5, 0.3])
        sun_dir = sun_dir / np.linalg.norm(sun_dir)
        total = sum(
            p.power(sun_dir, 1361.0, 301.15) for p in panels_3u
        )
        assert total > 0


class TestExcludeFaces:
    def test_exclude_one_face(self):
        panels = SolarPanel.cubesat_body("3U", "azur_3g30c", exclude_faces=["-Z"])
        assert len(panels) == 5
        names = [p.name for p in panels]
        assert "3U_-Z" not in names

    def test_exclude_multiple_faces(self):
        panels = SolarPanel.cubesat_body(
            "3U", "azur_3g30c", exclude_faces=["-Z", "+Z"]
        )
        assert len(panels) == 4
        names = [p.name for p in panels]
        assert "3U_-Z" not in names
        assert "3U_+Z" not in names

    def test_exclude_none_gives_all_faces(self):
        panels = SolarPanel.cubesat_body("3U", "azur_3g30c", exclude_faces=None)
        assert len(panels) == 6

    def test_exclude_empty_gives_all_faces(self):
        panels = SolarPanel.cubesat_body("3U", "azur_3g30c", exclude_faces=[])
        assert len(panels) == 6


class TestCubesatWithWings:
    def test_two_wings_default(self):
        panels = SolarPanel.cubesat_with_wings("3U", "azur_3g30c", wing_count=2)
        # 6 body panels + 2 wings
        assert len(panels) == 8
        wing_names = [p.name for p in panels if "wing" in p.name]
        assert len(wing_names) == 2
        assert "wing_+Y" in wing_names
        assert "wing_-Y" in wing_names

    def test_four_wings(self):
        panels = SolarPanel.cubesat_with_wings("3U", "azur_3g30c", wing_count=4)
        # 6 body panels + 4 wings
        assert len(panels) == 10
        wing_names = [p.name for p in panels if "wing" in p.name]
        assert len(wing_names) == 4

    def test_with_exclude_faces(self):
        panels = SolarPanel.cubesat_with_wings(
            "3U", "azur_3g30c", wing_count=2, exclude_faces=["-Z"]
        )
        # 5 body panels + 2 wings
        assert len(panels) == 7
        names = [p.name for p in panels]
        assert "3U_-Z" not in names

    def test_custom_wing_area(self):
        area = 0.05
        panels = SolarPanel.cubesat_with_wings(
            "3U", "azur_3g30c", wing_count=2, wing_area_m2=area
        )
        wings = [p for p in panels if "wing" in p.name]
        for wing in wings:
            # Wing area should be custom area * packing factor
            expected = area * wing.cell.packing_factor
            assert abs(wing.area_m2 - expected) < 1e-10

    def test_default_wing_area_is_2x_long_face(self):
        panels = SolarPanel.cubesat_with_wings("3U", "azur_3g30c", wing_count=2)
        wings = [p for p in panels if "wing" in p.name]
        # Default: 2 * 0.30 * 0.10 = 0.06 m^2 * packing_factor
        pf = wings[0].cell.packing_factor
        expected = 0.06 * pf
        assert abs(wings[0].area_m2 - expected) < 1e-10

    def test_invalid_wing_count_raises(self):
        with pytest.raises(ValueError):
            SolarPanel.cubesat_with_wings("3U", "azur_3g30c", wing_count=3)

    def test_6u_with_wings(self):
        panels = SolarPanel.cubesat_with_wings("6U", "azur_3g30c", wing_count=2)
        assert len(panels) == 8


class TestDeployed:
    def test_deployed_panel_creation(self):
        panel = SolarPanel.deployed(
            area_m2=0.06,
            cell_type="azur_3g30c",
            normal=np.array([0, 0, 1]),
            name="wing",
        )
        assert panel.name == "wing"
        assert abs(panel.area_m2 - 0.06) < 1e-10
