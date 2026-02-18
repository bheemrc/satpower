"""Pydantic request/response models for the satpower API."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# --- Enums ---

class PlotFormat(str, Enum):
    STRUCTURED = "structured"
    PNG_BASE64 = "png_base64"


# --- Request schemas ---

class OrbitRequest(BaseModel):
    altitude_km: float = Field(gt=0.0)
    inclination_deg: float = Field(ge=0.0, le=180.0)
    raan_deg: float = 0.0
    j2: bool = False
    eclipse_model: Literal["cylindrical", "conical"] = "cylindrical"


class SolarRequest(BaseModel):
    cell: str
    form_factor: Literal["1U", "3U", "6U"] = "3U"
    body_panels: bool = True
    exclude_faces: list[str] | None = None
    deployed_wings_count: Literal[2, 4] | None = None
    deployed_wings_area_m2: float | None = Field(default=None, gt=0.0)


class BatteryRequest(BaseModel):
    cell: str
    config: str = "2S1P"


class LoadRequest(BaseModel):
    name: str
    power_w: float = Field(ge=0.0)
    duty_cycle: float = Field(default=1.0, ge=0.0, le=1.0)
    trigger: Literal["always", "sunlight", "eclipse", "scheduled"] = "always"


class SimulationParametersRequest(BaseModel):
    duration_orbits: float = Field(default=10.0, gt=0.0)
    initial_soc: float = Field(default=1.0, ge=0.0, le=1.0)
    dt_max: float = Field(default=30.0, gt=0.0)


class SimulationRequest(BaseModel):
    """Flattened simulation request — everything needed to run a simulation."""
    name: str = "API Simulation"
    orbit: OrbitRequest
    solar: SolarRequest
    battery: BatteryRequest
    loads: list[LoadRequest] = Field(default_factory=list)
    simulation: SimulationParametersRequest = Field(
        default_factory=SimulationParametersRequest
    )
    eps_board: str | None = None
    plot_format: PlotFormat = PlotFormat.STRUCTURED
    validate_system: bool = False


class PresetSimulationRequest(BaseModel):
    """Run a bundled preset mission with optional overrides."""
    preset_name: str
    overrides: dict[str, Any] = Field(default_factory=dict)
    plot_format: PlotFormat = PlotFormat.STRUCTURED


# --- Response schemas ---

class TimeSeriesData(BaseModel):
    label: str
    unit: str
    x: list[float]
    y: list[float]


class PlotData(BaseModel):
    plot_type: str
    format: PlotFormat
    time_series: list[TimeSeriesData] | None = None
    png_base64: str | None = None
    eclipse_regions: list[tuple[float, float]] = Field(default_factory=list)


class SimulationSummary(BaseModel):
    min_soc: float
    max_soc: float
    worst_case_dod: float
    avg_power_generated_w: float
    avg_power_consumed_w: float
    power_margin_w: float
    energy_balance_per_orbit_wh: float
    eclipse_fraction: float
    min_battery_voltage_v: float
    max_battery_voltage_v: float
    duration_orbits: float


class PowerBudgetResponse(BaseModel):
    mission_name: str
    subsystems: list[dict]
    avg_generated_w: float
    avg_consumed_w: float
    power_margin_w: float
    eclipse_fraction: float
    worst_dod: float
    min_soc: float
    battery_energy_wh: float
    verdict: str


class ValidationResponse(BaseModel):
    passed: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class SimulationResponse(BaseModel):
    simulation_id: str
    name: str
    summary: SimulationSummary
    power_budget: PowerBudgetResponse
    validation: ValidationResponse | None = None
    plots: list[PlotData] = Field(default_factory=list)


class ComponentInfo(BaseModel):
    name: str
    category: str
    highlights: dict[str, Any] = Field(default_factory=dict)


class ComponentListResponse(BaseModel):
    category: str
    components: list[ComponentInfo]


class ComponentDetailResponse(BaseModel):
    name: str
    category: str
    data: dict[str, Any]


class PresetInfo(BaseModel):
    name: str
    application: str = ""


class PresetListResponse(BaseModel):
    presets: list[PresetInfo]
