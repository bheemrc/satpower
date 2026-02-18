"""Thin orchestration layer — connects API schemas to satpower internals."""

from __future__ import annotations

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor

from satpower.api._errors import (
    ComponentNotFoundError,
    InvalidConfigurationError,
    PresetNotFoundError,
    SimulationError,
)
from satpower.api._schemas import (
    ComponentDetailResponse,
    ComponentInfo,
    ComponentListResponse,
    PlotFormat,
    PowerBudgetResponse,
    PresetInfo,
    PresetListResponse,
    PresetSimulationRequest,
    SimulationRequest,
    SimulationResponse,
    SimulationSummary,
    ValidationResponse,
)
from satpower.api._serializers import (
    serialize_plot_battery_voltage,
    serialize_plot_power_balance,
    serialize_plot_soc,
)
from satpower.data._registry import registry
from satpower.mission._builder import build_simulation, load_mission
from satpower.mission._config import (
    BatteryConfig,
    DeployedWingsConfig,
    LoadConfig,
    MissionConfig,
    OrbitConfig,
    SatelliteConfig,
    SimulationConfig,
    SolarConfig,
)

_executor = ThreadPoolExecutor(max_workers=4)


def _request_to_mission_config(request: SimulationRequest) -> MissionConfig:
    """Convert a SimulationRequest into a MissionConfig."""
    deployed_wings = None
    if request.solar.deployed_wings_count is not None:
        deployed_wings = DeployedWingsConfig(
            count=request.solar.deployed_wings_count,
            area_m2=request.solar.deployed_wings_area_m2,
        )

    return MissionConfig(
        name=request.name,
        orbit=OrbitConfig(
            altitude_km=request.orbit.altitude_km,
            inclination_deg=request.orbit.inclination_deg,
            raan_deg=request.orbit.raan_deg,
            j2=request.orbit.j2,
            eclipse_model=request.orbit.eclipse_model,
        ),
        satellite=SatelliteConfig(
            form_factor=request.solar.form_factor,
            eps_board=request.eps_board,
            solar=SolarConfig(
                cell=request.solar.cell,
                body_panels=request.solar.body_panels,
                exclude_faces=request.solar.exclude_faces,
                deployed_wings=deployed_wings,
            ),
            battery=BatteryConfig(
                cell=request.battery.cell,
                config=request.battery.config,
            ),
        ),
        loads=[
            LoadConfig(
                name=load.name,
                power_w=load.power_w,
                duty_cycle=load.duty_cycle,
                trigger=load.trigger,
            )
            for load in request.loads
        ],
        simulation=SimulationConfig(
            duration_orbits=request.simulation.duration_orbits,
            initial_soc=request.simulation.initial_soc,
            dt_max=request.simulation.dt_max,
        ),
    )


def run_simulation(request: SimulationRequest) -> SimulationResponse:
    """Run a simulation from an API request and return a structured response."""
    # Validate component names exist
    try:
        registry.get_solar_cell(request.solar.cell)
    except Exception:
        raise ComponentNotFoundError("solar_cell", request.solar.cell)

    try:
        registry.get_battery_cell(request.battery.cell)
    except Exception:
        raise ComponentNotFoundError("battery_cell", request.battery.cell)

    if request.eps_board:
        try:
            registry.get_eps(request.eps_board)
        except Exception:
            raise ComponentNotFoundError("eps_board", request.eps_board)

    # Build and run simulation
    try:
        config = _request_to_mission_config(request)
        sim = build_simulation(config)
        results = sim.run(
            duration_orbits=config.simulation.duration_orbits,
            dt_max=config.simulation.dt_max,
        )
    except Exception as e:
        raise SimulationError(str(e))

    # Build response
    summary_dict = results.summary()
    summary = SimulationSummary(**summary_dict)

    # Power budget
    from satpower.loads._profile import LoadProfile
    from satpower.battery._pack import BatteryPack

    loads = LoadProfile()
    for load in request.loads:
        loads.add_mode(
            name=load.name,
            power_w=load.power_w,
            duty_cycle=load.duty_cycle,
            trigger=load.trigger,
        )

    battery = BatteryPack.from_cell(request.battery.cell, request.battery.config)
    report = results.report(loads, battery, request.name)
    power_budget = PowerBudgetResponse(
        mission_name=report.mission_name,
        subsystems=report.subsystems,
        avg_generated_w=report.avg_generated_w,
        avg_consumed_w=report.avg_consumed_w,
        power_margin_w=report.power_margin_w,
        eclipse_fraction=report.eclipse_fraction,
        worst_dod=report.worst_dod,
        min_soc=report.min_soc,
        battery_energy_wh=report.battery_energy_wh,
        verdict=report.verdict,
    )

    # Validation (optional)
    validation = None
    if request.validate_system and request.eps_board:
        from satpower.validation._checks import validate_system as _validate
        from satpower.regulation._eps_board import EPSBoard
        from satpower.solar._panel import SolarPanel

        eps = EPSBoard.from_datasheet(request.eps_board)
        sc = request.solar
        if sc.deployed_wings_count is not None:
            panels = SolarPanel.cubesat_with_wings(
                form_factor=sc.form_factor,
                cell_type=sc.cell,
                wing_count=sc.deployed_wings_count,
                wing_area_m2=sc.deployed_wings_area_m2,
                exclude_faces=sc.exclude_faces,
            )
        elif sc.body_panels:
            panels = SolarPanel.cubesat_body(
                form_factor=sc.form_factor,
                cell_type=sc.cell,
                exclude_faces=sc.exclude_faces,
            )
        else:
            panels = []

        val_result = _validate(eps, battery, panels)
        validation = ValidationResponse(
            passed=val_result.passed,
            warnings=val_result.warnings,
            errors=val_result.errors,
        )

    # Plots
    fmt = request.plot_format
    plots = [
        serialize_plot_soc(results, fmt),
        serialize_plot_power_balance(results, fmt),
        serialize_plot_battery_voltage(results, fmt),
    ]

    return SimulationResponse(
        simulation_id=str(uuid.uuid4()),
        name=request.name,
        summary=summary,
        power_budget=power_budget,
        validation=validation,
        plots=plots,
    )


async def run_simulation_async(request: SimulationRequest) -> SimulationResponse:
    """Async wrapper for run_simulation (CPU-bound, runs in thread pool)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, run_simulation, request)


def run_preset(request: PresetSimulationRequest) -> SimulationResponse:
    """Run a bundled preset mission."""
    available = registry.list_missions()
    if request.preset_name not in available:
        raise PresetNotFoundError(request.preset_name)

    config = load_mission(request.preset_name)

    # Build SimulationRequest from preset config
    from satpower.api._schemas import (
        BatteryRequest,
        LoadRequest,
        OrbitRequest,
        SimulationParametersRequest,
        SolarRequest,
    )

    solar_req = SolarRequest(
        cell=config.satellite.solar.cell,
        form_factor=config.satellite.form_factor,
        body_panels=config.satellite.solar.body_panels,
        exclude_faces=config.satellite.solar.exclude_faces,
    )
    if config.satellite.solar.deployed_wings:
        solar_req.deployed_wings_count = config.satellite.solar.deployed_wings.count
        solar_req.deployed_wings_area_m2 = config.satellite.solar.deployed_wings.area_m2

    sim_request = SimulationRequest(
        name=config.name,
        orbit=OrbitRequest(
            altitude_km=config.orbit.altitude_km,
            inclination_deg=config.orbit.inclination_deg,
            raan_deg=config.orbit.raan_deg,
            j2=config.orbit.j2,
            eclipse_model=config.orbit.eclipse_model,
        ),
        solar=solar_req,
        battery=BatteryRequest(
            cell=config.satellite.battery.cell,
            config=config.satellite.battery.config,
        ),
        loads=[
            LoadRequest(
                name=load.name,
                power_w=load.power_w,
                duty_cycle=load.duty_cycle,
                trigger=load.trigger,
            )
            for load in config.loads
        ],
        simulation=SimulationParametersRequest(
            duration_orbits=config.simulation.duration_orbits,
            initial_soc=config.simulation.initial_soc,
            dt_max=config.simulation.dt_max,
        ),
        eps_board=config.satellite.eps_board,
        plot_format=request.plot_format,
    )

    # Apply overrides
    unknown_overrides = []
    for key, value in request.overrides.items():
        if hasattr(sim_request, key):
            setattr(sim_request, key, value)
        else:
            unknown_overrides.append(key)

    if unknown_overrides:
        raise InvalidConfigurationError(
            f"Unknown override keys: {', '.join(sorted(unknown_overrides))}"
        )

    return run_simulation(sim_request)


def list_components(category: str) -> ComponentListResponse:
    """List all components in a category."""
    if category == "solar_cells":
        names = registry.list_solar_cells()
        components = []
        for name in names:
            data = registry.get_solar_cell(name)
            components.append(
                ComponentInfo(
                    name=name,
                    category=category,
                    highlights={
                        "efficiency": data.parameters.efficiency,
                        "area_cm2": data.parameters.area_cm2,
                    },
                )
            )
    elif category == "battery_cells":
        names = registry.list_battery_cells()
        components = []
        for name in names:
            data = registry.get_battery_cell(name)
            components.append(
                ComponentInfo(
                    name=name,
                    category=category,
                    highlights={
                        "capacity_ah": data.capacity_ah,
                        "nominal_voltage_v": data.nominal_voltage_v,
                    },
                )
            )
    elif category == "eps":
        names = registry.list_eps()
        components = []
        for name in names:
            data = registry.get_eps(name)
            components.append(
                ComponentInfo(
                    name=name,
                    category=category,
                    highlights={
                        "bus_voltage_v": data.bus_voltage_v,
                    },
                )
            )
    else:
        raise InvalidConfigurationError(f"Unknown component category: {category!r}")

    return ComponentListResponse(category=category, components=components)


def get_component(category: str, name: str) -> ComponentDetailResponse:
    """Get full details for a single component."""
    try:
        if category == "solar_cells":
            data = registry.get_solar_cell(name)
        elif category == "battery_cells":
            data = registry.get_battery_cell(name)
        elif category == "eps":
            data = registry.get_eps(name)
        else:
            raise InvalidConfigurationError(f"Unknown component category: {category!r}")
    except FileNotFoundError:
        raise ComponentNotFoundError(category, name)

    return ComponentDetailResponse(
        name=name,
        category=category,
        data=data.model_dump(),
    )


def get_presets() -> PresetListResponse:
    """List all bundled mission presets."""
    names = registry.list_missions()
    presets = []
    for name in names:
        try:
            config = load_mission(name)
            presets.append(PresetInfo(name=name, application=config.application))
        except Exception:
            presets.append(PresetInfo(name=name))

    return PresetListResponse(presets=presets)
