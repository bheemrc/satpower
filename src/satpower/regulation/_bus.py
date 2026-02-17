"""Bus voltage regulation and load switching."""

from __future__ import annotations

from satpower.regulation._converter import DcDcConverter


class PowerBus:
    """Spacecraft power bus.

    Manages bus voltage and converter losses between solar array,
    battery, and loads. Applies DC-DC converter efficiency to both
    charging (solar → battery) and discharging (battery → loads) paths.
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
        Applies converter efficiency in both directions:
        - Discharge: battery must supply load_power / efficiency
        - Charge: battery receives excess solar * efficiency

        Parameters
        ----------
        solar_power : Total solar array power (W)
        load_power : Total load power demand (W)
        battery_voltage : Current battery terminal voltage (V)
        """
        if battery_voltage <= 0:
            return 0.0

        eff = self._converter.efficiency

        # Solar power goes through MPPT/converter to bus
        solar_to_bus = solar_power * eff

        # Net power balance at the bus
        net_power_bus = load_power - solar_to_bus

        if net_power_bus > 0:
            # Discharging: battery must supply more than bus needs due to
            # converter loss from battery voltage to bus voltage
            battery_power = net_power_bus / eff
        else:
            # Charging: excess solar charges battery with converter loss
            battery_power = net_power_bus * eff

        return battery_power / battery_voltage
