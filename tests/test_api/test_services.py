"""Tests for satpower API services."""

import pytest

from satpower.api import (
    SimulationRequest,
    SimulationResponse,
    OrbitRequest,
    SolarRequest,
    BatteryRequest,
    LoadRequest,
    SimulationParametersRequest,
    PresetSimulationRequest,
    PlotFormat,
    run_simulation,
    run_preset,
    list_components,
    get_component,
    get_presets,
    SatpowerAPIError,
    ComponentNotFoundError,
    SimulationError,
    PresetNotFoundError,
)


@pytest.fixture
def basic_request():
    return SimulationRequest(
        name="Test Mission",
        orbit=OrbitRequest(altitude_km=500, inclination_deg=45),
        solar=SolarRequest(cell="azur_3g30c", form_factor="3U"),
        battery=BatteryRequest(cell="panasonic_ncr18650b", config="2S2P"),
        loads=[
            LoadRequest(name="obc", power_w=0.5),
            LoadRequest(name="comms", power_w=4.0, duty_cycle=0.15),
        ],
        simulation=SimulationParametersRequest(duration_orbits=2, dt_max=60.0),
    )


class TestRunSimulation:
    def test_round_trip(self, basic_request):
        """Full simulation request → response with valid summary."""
        response = run_simulation(basic_request)
        assert isinstance(response, SimulationResponse)
        assert response.name == "Test Mission"
        assert response.simulation_id  # non-empty UUID
        assert response.summary.min_soc >= 0
        assert response.summary.max_soc <= 1.0
        assert response.summary.duration_orbits > 0

    def test_power_budget_in_response(self, basic_request):
        """Response should contain a valid power budget."""
        response = run_simulation(basic_request)
        assert response.power_budget.mission_name == "Test Mission"
        assert response.power_budget.avg_generated_w >= 0

    def test_plots_structured(self, basic_request):
        """Structured plots should contain time series data."""
        basic_request.plot_format = PlotFormat.STRUCTURED
        response = run_simulation(basic_request)
        assert len(response.plots) == 3
        for plot in response.plots:
            assert plot.format == PlotFormat.STRUCTURED
            assert plot.time_series is not None
            assert len(plot.time_series) > 0

    def test_plots_base64(self, basic_request):
        """Base64 plots should contain PNG data."""
        basic_request.plot_format = PlotFormat.PNG_BASE64
        response = run_simulation(basic_request)
        assert len(response.plots) == 3
        for plot in response.plots:
            assert plot.format == PlotFormat.PNG_BASE64
            assert plot.png_base64 is not None
            assert len(plot.png_base64) > 100  # non-trivial PNG data

    def test_bad_solar_cell_raises(self):
        request = SimulationRequest(
            orbit=OrbitRequest(altitude_km=500, inclination_deg=45),
            solar=SolarRequest(cell="nonexistent_cell"),
            battery=BatteryRequest(cell="panasonic_ncr18650b"),
        )
        with pytest.raises(ComponentNotFoundError):
            run_simulation(request)

    def test_bad_battery_cell_raises(self):
        request = SimulationRequest(
            orbit=OrbitRequest(altitude_km=500, inclination_deg=45),
            solar=SolarRequest(cell="azur_3g30c"),
            battery=BatteryRequest(cell="nonexistent_battery"),
        )
        with pytest.raises(ComponentNotFoundError):
            run_simulation(request)


class TestComponentListing:
    def test_list_solar_cells(self):
        response = list_components("solar_cells")
        assert response.category == "solar_cells"
        assert len(response.components) >= 6

    def test_list_battery_cells(self):
        response = list_components("battery_cells")
        assert response.category == "battery_cells"
        assert len(response.components) >= 5

    def test_list_eps(self):
        response = list_components("eps")
        assert response.category == "eps"
        assert len(response.components) >= 4

    def test_invalid_category(self):
        with pytest.raises(SatpowerAPIError):
            list_components("nonexistent")


class TestComponentDetail:
    def test_valid_solar_cell(self):
        response = get_component("solar_cells", "azur_3g30c")
        assert response.name == "azur_3g30c"
        assert response.category == "solar_cells"
        assert "parameters" in response.data

    def test_invalid_name_raises(self):
        with pytest.raises(ComponentNotFoundError):
            get_component("solar_cells", "does_not_exist")


class TestPresets:
    def test_list_presets(self):
        response = get_presets()
        assert len(response.presets) >= 5

    def test_run_preset(self):
        response = run_preset(PresetSimulationRequest(
            preset_name="earth_observation_3u",
            plot_format=PlotFormat.STRUCTURED,
        ))
        assert isinstance(response, SimulationResponse)
        assert response.summary.duration_orbits > 0

    def test_invalid_preset_raises(self):
        with pytest.raises(PresetNotFoundError):
            run_preset(PresetSimulationRequest(preset_name="nonexistent_preset"))
