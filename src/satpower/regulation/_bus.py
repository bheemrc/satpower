"""Bus voltage regulation and load switching."""

from __future__ import annotations

from satpower.regulation._converter import DcDcConverter


class PowerBus:
    """Spacecraft power bus.

    Manages bus voltage and converter losses between solar array,
    battery, and loads.
    """

    def __init__(
        self,
        bus_voltage: float = 3.3,
        converter: DcDcConverter | None = None,
    ):
        self._bus_voltage = bus_voltage
        self._converter = converter or DcDcConverter()

    @property
    def bus_voltage(self) -> float:
        return self._bus_voltage

    @property
    def converter_efficiency(self) -> float:
        return self._converter.efficiency

    def net_battery_current(
        self,
        solar_power: float,
        load_power: float,
        battery_voltage: float,
    ) -> float:
        """Compute net current flowing into/out of battery.

        Positive = discharge (load > solar), negative = charge (solar > load).

        Parameters
        ----------
        solar_power : Total solar array power (W)
        load_power : Total load power demand (W)
        battery_voltage : Current battery terminal voltage (V)
        """
        if battery_voltage <= 0:
            return 0.0

        # Solar power goes through MPPT/converter to bus
        solar_to_bus = self._converter.output_power(solar_power)

        # Net power the battery must provide (positive = discharge)
        net_power = load_power - solar_to_bus

        # Convert to battery current
        return net_power / battery_voltage
