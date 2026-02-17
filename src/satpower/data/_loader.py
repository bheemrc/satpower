"""YAML loading and Pydantic validation for component datasheets."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel

_DATA_DIR = Path(__file__).parent


class DiodeModelData(BaseModel):
    ideality_factor: float
    series_resistance_ohm: float
    shunt_resistance_ohm: float


class TemperatureCoeffData(BaseModel):
    dvoc_dt_mv_per_c: float
    disc_dt_ua_cm2_per_c: float
    dpmp_dt_percent_per_c: float


class RadiationData(BaseModel):
    remaining_factor_1e14: float
    remaining_factor_1e15: float


class OpticalData(BaseModel):
    absorptance: float
    emittance: float
    packing_factor: float


class TestConditionsData(BaseModel):
    spectrum: str
    irradiance_w_m2: float
    temperature_c: float


class SolarCellParams(BaseModel):
    voc_v: float
    isc_a: float
    vmp_v: float
    imp_a: float
    efficiency: float
    area_cm2: float


class SolarCellData(BaseModel):
    name: str
    type: str
    junctions: list[str]
    test_conditions: TestConditionsData
    parameters: SolarCellParams
    diode_model: DiodeModelData
    temperature_coefficients: TemperatureCoeffData
    radiation: RadiationData
    optical: OpticalData


class TheveninModelData(BaseModel):
    ro_ohm: float
    r1_ohm: float
    c1_f: float
    r2_ohm: float = 0.0
    c2_f: float = 0.0


class BatteryTemperatureData(BaseModel):
    ro_activation_energy_j: float
    reference_temp_c: float
    capacity_derating: list[list[float]]


class BatteryAgingData(BaseModel):
    calendar_fade_per_year_25c: float
    cycle_fade_per_cycle_50dod: float
    cycle_fade_per_cycle_100dod: float


class BatteryCellData(BaseModel):
    name: str
    chemistry: str
    form_factor: str
    nominal_voltage_v: float
    capacity_ah: float
    max_charge_voltage_v: float
    min_discharge_voltage_v: float
    max_charge_current_a: float
    max_discharge_current_a: float
    mass_g: float
    thevenin_model: TheveninModelData
    ocv_soc_table: list[list[float]]
    temperature: BatteryTemperatureData
    aging: BatteryAgingData


class EPSData(BaseModel):
    name: str
    bus_voltage_v: float
    bus_voltage_range_v: list[float]
    max_solar_input_v: float
    max_solar_input_a: float
    converter_efficiency: float
    mppt_efficiency: float
    battery_config: str
    num_solar_inputs: int
    max_output_channels: int
    mass_g: float


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_solar_cell(name: str) -> SolarCellData:
    """Load a solar cell datasheet by name (e.g. 'azur_3g30c')."""
    path = _DATA_DIR / "cells" / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Solar cell datasheet not found: {name}")
    return SolarCellData(**_load_yaml(path))


def load_battery_cell(name: str) -> BatteryCellData:
    """Load a battery cell datasheet by name (e.g. 'panasonic_ncr18650b')."""
    path = _DATA_DIR / "batteries" / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Battery cell datasheet not found: {name}")
    return BatteryCellData(**_load_yaml(path))


def load_eps(name: str) -> EPSData:
    """Load an EPS board profile by name (e.g. 'gomspace_p31u')."""
    path = _DATA_DIR / "eps" / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"EPS profile not found: {name}")
    return EPSData(**_load_yaml(path))
