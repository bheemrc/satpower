"""EPS board abstraction — loads YAML datasheet, creates converter + bus."""

from __future__ import annotations

from satpower.data._loader import load_eps, EPSData
from satpower.regulation._converter import DcDcConverter
from satpower.regulation._bus import PowerBus


class EPSBoard:
    """EPS board loaded from a component datasheet.

    Wraps converter efficiency and bus voltage from the YAML into
    a DcDcConverter and PowerBus, ready for simulation.
    """

    def __init__(self, data: EPSData):
        self._data = data
        self._converter = DcDcConverter(
            efficiency=data.converter_efficiency,
            name=data.name,
        )
        self._bus = PowerBus(
            bus_voltage=data.bus_voltage_v,
            converter=self._converter,
        )

    @classmethod
    def from_datasheet(cls, name: str) -> EPSBoard:
        """Load EPS board from YAML datasheet by name."""
        return cls(load_eps(name))

    @property
    def name(self) -> str:
        return self._data.name

    @property
    def bus(self) -> PowerBus:
        return self._bus

    @property
    def bus_voltage(self) -> float:
        return self._data.bus_voltage_v

    @property
    def bus_voltage_range(self) -> tuple[float, float]:
        r = self._data.bus_voltage_range_v
        return (r[0], r[1])

    @property
    def mppt_efficiency(self) -> float:
        return self._data.mppt_efficiency

    @property
    def converter_efficiency(self) -> float:
        return self._data.converter_efficiency

    @property
    def max_solar_input_v(self) -> float:
        return self._data.max_solar_input_v

    @property
    def max_solar_input_a(self) -> float:
        return self._data.max_solar_input_a

    @property
    def battery_config(self) -> str:
        return self._data.battery_config

    @property
    def num_solar_inputs(self) -> int:
        return self._data.num_solar_inputs

    @property
    def max_output_channels(self) -> int:
        return self._data.max_output_channels

    @property
    def mass_g(self) -> float:
        return self._data.mass_g
