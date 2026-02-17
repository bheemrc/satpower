"""Tests for component registry — verify every YAML loads without error."""

import pytest

from satpower.data._registry import registry


EXPECTED_CELLS = [
    "azur_3g30c",
    "azur_4g32c",
    "cesi_ctj30",
    "solaero_ztj",
    "spectrolab_utj",
    "spectrolab_xtj_prime",
]

EXPECTED_BATTERIES = [
    "lg_mj1",
    "panasonic_ncr18650b",
    "saft_mp176065",
    "samsung_inr18650_30q",
    "sony_vtc6",
]

EXPECTED_EPS = [
    "clydespace_3g_eps",
    "endurosat_eps_i_plus",
    "gomspace_p31u",
    "isis_ieps",
]


class TestRegistryListing:
    def test_list_solar_cells(self):
        cells = sorted(registry.list_solar_cells())
        assert cells == EXPECTED_CELLS

    def test_list_battery_cells(self):
        batteries = sorted(registry.list_battery_cells())
        assert batteries == EXPECTED_BATTERIES

    def test_list_eps(self):
        eps = sorted(registry.list_eps())
        assert eps == EXPECTED_EPS


class TestSolarCellLoading:
    @pytest.mark.parametrize("name", EXPECTED_CELLS)
    def test_load_solar_cell(self, name):
        data = registry.get_solar_cell(name)
        assert data.name
        assert data.parameters.efficiency > 0
        assert data.parameters.voc_v > 0
        assert data.parameters.isc_a > 0
        assert data.parameters.area_cm2 > 0

    def test_unknown_solar_cell_raises(self):
        with pytest.raises(FileNotFoundError):
            registry.get_solar_cell("nonexistent_cell")


class TestBatteryCellLoading:
    @pytest.mark.parametrize("name", EXPECTED_BATTERIES)
    def test_load_battery_cell(self, name):
        data = registry.get_battery_cell(name)
        assert data.name
        assert data.capacity_ah > 0
        assert data.nominal_voltage_v > 0
        assert data.max_charge_voltage_v > data.min_discharge_voltage_v

    def test_unknown_battery_raises(self):
        with pytest.raises(FileNotFoundError):
            registry.get_battery_cell("nonexistent_battery")


class TestEPSLoading:
    @pytest.mark.parametrize("name", EXPECTED_EPS)
    def test_load_eps(self, name):
        data = registry.get_eps(name)
        assert data.name
        assert data.bus_voltage_v > 0
        assert data.converter_efficiency > 0
        assert data.num_solar_inputs > 0

    def test_unknown_eps_raises(self):
        with pytest.raises(FileNotFoundError):
            registry.get_eps("nonexistent_eps")
