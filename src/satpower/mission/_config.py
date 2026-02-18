"""Pydantic models for mission YAML configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OrbitConfig(BaseModel):
    type: str = "circular"
    altitude_km: float
    inclination_deg: float
    raan_deg: float = 0.0
    j2: bool = False
    eclipse_model: str = "cylindrical"


class DeployedWingsConfig(BaseModel):
    count: int = 2
    area_m2: float | None = None


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
    power_w: float
    duty_cycle: float = 1.0
    trigger: str = "always"


class SatelliteConfig(BaseModel):
    form_factor: str = "3U"
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
    duration_orbits: float = 10.0
    initial_soc: float = 1.0
    dt_max: float = 30.0
    thermal: ThermalModelConfig = Field(default_factory=ThermalModelConfig)


class MissionConfig(BaseModel):
    name: str
    application: str = ""
    orbit: OrbitConfig
    satellite: SatelliteConfig
    loads: list[LoadConfig] = Field(default_factory=list)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
