"""Component lookup by name — scans data directories on first access."""

from __future__ import annotations

from pathlib import Path

from satpower.data._loader import (
    SolarCellData,
    BatteryCellData,
    EPSData,
    load_solar_cell,
    load_battery_cell,
    load_eps,
)

_DATA_DIR = Path(__file__).parent


class ComponentRegistry:
    """Lazy-loading registry for component datasheets."""

    def list_solar_cells(self) -> list[str]:
        return [p.stem for p in (_DATA_DIR / "cells").glob("*.yaml")]

    def list_battery_cells(self) -> list[str]:
        return [p.stem for p in (_DATA_DIR / "batteries").glob("*.yaml")]

    def list_eps(self) -> list[str]:
        return [p.stem for p in (_DATA_DIR / "eps").glob("*.yaml")]

    def get_solar_cell(self, name: str) -> SolarCellData:
        return load_solar_cell(name)

    def get_battery_cell(self, name: str) -> BatteryCellData:
        return load_battery_cell(name)

    def get_eps(self, name: str) -> EPSData:
        return load_eps(name)

    def list_missions(self) -> list[str]:
        missions_dir = _DATA_DIR / "missions"
        if not missions_dir.exists():
            return []
        return [p.stem for p in missions_dir.glob("*.yaml")]


registry = ComponentRegistry()
