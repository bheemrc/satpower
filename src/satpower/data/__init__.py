"""Component database — YAML datasheets for solar cells, batteries, and EPS boards."""

from satpower.data._loader import (
    SolarCellData,
    BatteryCellData,
    EPSData,
    load_solar_cell,
    load_battery_cell,
    load_eps,
)
from satpower.data._registry import registry

__all__ = [
    "SolarCellData",
    "BatteryCellData",
    "EPSData",
    "load_solar_cell",
    "load_battery_cell",
    "load_eps",
    "registry",
]
