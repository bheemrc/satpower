"""Pydantic models for mission YAML configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class OrbitConfig(BaseModel):
    type: Literal["circular"] = "circular"
    altitude_km: float = Field(gt=0.0)
    inclination_deg: float = Field(ge=0.0, le=180.0)
    raan_deg: float = 0.0
    j2: bool = False
    eclipse_model: Literal["cylindrical", "conical"] = "cylindrical"


class DeployedWingsConfig(BaseModel):
    count: Literal[2, 4] = 2
    area_m2: float | None = Field(default=None, gt=0.0)


class SolarConfig(BaseModel):
    cell: str
    body_panels: bool = True
    exclude_faces: list[str] | None = None
    deployed_wings: DeployedWingsConfig | None = None


class BatteryConfig(BaseModel):
    cell: str
    config: str = "2S1P"


class LoadConfig(BaseModel):
    name: str
    power_w: float = Field(ge=0.0)
    duty_cycle: float = Field(default=1.0, ge=0.0, le=1.0)
    trigger: Literal["always", "sunlight", "eclipse", "scheduled"] = "always"


class SatelliteConfig(BaseModel):
    form_factor: Literal["1U", "3U", "6U"] = "3U"
    eps_board: str | None = None
    solar: SolarConfig
    battery: BatteryConfig
    loads: list[LoadConfig] = Field(default_factory=list)


class ThermalModelConfig(BaseModel):
    enabled: bool = False
    panel_thermal_mass_j_per_k: float = 450.0
    battery_thermal_mass_j_per_k: float = 95.0
    spacecraft_interior_temp_k: float = 293.15


class SimulationConfig(BaseModel):
    duration_orbits: float = Field(default=10.0, gt=0.0)
    initial_soc: float = Field(default=1.0, ge=0.0, le=1.0)
    dt_max: float = Field(default=30.0, gt=0.0)
    thermal: ThermalModelConfig = Field(default_factory=ThermalModelConfig)


class MissionConfig(BaseModel):
    name: str
    application: str = ""
    orbit: OrbitConfig
    satellite: SatelliteConfig
    loads: list[LoadConfig] = Field(default_factory=list)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
