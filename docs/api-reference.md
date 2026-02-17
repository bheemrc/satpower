# API Reference

## Top-level imports

All core classes are available from `import satpower as sp`:

```python
import satpower as sp

sp.Orbit
sp.SolarCell
sp.SolarPanel
sp.BatteryCell
sp.BatteryPack
sp.LoadProfile
sp.LoadMode
sp.PowerBus
sp.DcDcConverter
sp.EPSBoard
sp.Simulation
sp.SimulationResults
sp.EclipseModel
sp.OrbitalEnvironment
```

---

## `satpower.orbit`

### `Orbit`

```python
Orbit.circular(altitude_km, inclination_deg, raan_deg=0.0) -> Orbit
```

Creates a circular LEO orbit. Properties: `period`, `altitude_km`, `altitude_m`, `inclination_deg`, `semi_major_axis`.

```python
orbit.propagate(times: np.ndarray) -> OrbitState
```

Returns position/velocity in ECI frame at given times (seconds from epoch).

### `OrbitState`

Dataclass with `time`, `position` (N,3), `velocity` (N,3), and `altitude` property.

### `EclipseModel`

```python
model = EclipseModel(method="cylindrical")
model.shadow_fraction(sat_pos, sun_pos) -> float | np.ndarray  # 0=sun, 1=shadow
model.find_transitions(sat_positions, sun_positions, times) -> list[EclipseEvent]
```

### `OrbitalEnvironment`

```python
env = OrbitalEnvironment(solar_constant=1361.0)
env.solar_flux(distance_au=1.0) -> float
env.earth_albedo_flux(altitude_m) -> float
env.earth_ir_flux(altitude_m) -> float
env.beta_angle(inclination_rad, raan_rad, sun_ecliptic_lon_rad) -> float
```

---

## `satpower.solar`

### `SolarCell`

```python
SolarCell.from_datasheet(name: str) -> SolarCell
```

Properties: `name`, `area_cm2`, `area_m2`, `efficiency`, `packing_factor`, `voc`, `isc`.

Methods:
```python
cell.iv_curve(irradiance, temperature_k, voltage) -> np.ndarray
cell.mpp(irradiance, temperature_k) -> (v_mp, i_mp)
cell.power_at_mpp(irradiance, temperature_k) -> float
```

### `SolarPanel`

```python
# Body-mounted panels
SolarPanel.cubesat_body(
    form_factor: str,        # "1U", "3U", "6U"
    cell_type: str,          # cell name from database
    exclude_faces: list[str] | None = None,
) -> list[SolarPanel]

# Body panels + deployed wings
SolarPanel.cubesat_with_wings(
    form_factor: str,
    cell_type: str,
    wing_count: int = 2,           # 2 or 4
    wing_area_m2: float | None = None,
    exclude_faces: list[str] | None = None,
) -> list[SolarPanel]

# Single custom panel
SolarPanel.deployed(
    area_m2: float,
    cell_type: str,
    normal: np.ndarray,
    name: str = "deployed",
) -> SolarPanel
```

Properties: `area_m2`, `normal`, `name`, `cell`.

```python
panel.power(sun_direction, irradiance, temperature_k, mppt_efficiency=0.97) -> float
```

---

## `satpower.battery`

### `BatteryCell`

```python
BatteryCell.from_datasheet(name: str) -> BatteryCell
```

Properties: `name`, `capacity_ah`, `capacity_wh`, `nominal_voltage`, `max_voltage`, `min_voltage`.

Methods:
```python
cell.ocv(soc) -> float
cell.internal_resistance(soc, temperature_k=298.15) -> float
cell.terminal_voltage(soc, current, temperature_k, v_rc1=0, v_rc2=0) -> float
cell.derivatives(current, v_rc1, v_rc2=0) -> (dv_rc1_dt, dv_rc2_dt)
```

### `BatteryPack`

```python
BatteryPack.from_cell(cell_name: str, config: str) -> BatteryPack
```

Properties: `cell`, `n_series`, `n_parallel`, `capacity_ah`, `energy_wh`, `nominal_voltage`, `max_voltage`, `min_voltage`.

Methods: `terminal_voltage(...)`, `derivatives(...)` -- same as BatteryCell but scaled for pack.

---

## `satpower.loads`

### `LoadProfile`

```python
loads = LoadProfile()
loads.add_mode(name, power_w, duty_cycle=1.0, trigger="always", priority=0)
```

Properties: `modes` (list of `LoadMode`).

Methods:
```python
loads.power_at(time, in_eclipse=False) -> float
loads.active_modes(time, in_eclipse=False) -> list[str]
loads.orbit_average_power(eclipse_fraction) -> float
```

### `LoadMode`

Dataclass: `name`, `power_w`, `duty_cycle`, `trigger`, `priority`.

### `SUBSYSTEM_POWER`

Dict of typical CubeSat subsystem power draws (W):

```python
from satpower.loads import SUBSYSTEM_POWER
# Keys: obc_arm, obc_msp430, adcs_magnetorquer, adcs_reaction_wheel,
#        uhf_transceiver, sband_transmitter, xband_transmitter,
#        camera_vis, camera_multispectral, gps_receiver, star_tracker,
#        heater_battery, beacon, ais_receiver
```

---

## `satpower.regulation`

### `EPSBoard`

```python
EPSBoard.from_datasheet(name: str) -> EPSBoard
```

Properties: `name`, `bus`, `bus_voltage`, `bus_voltage_range`, `mppt_efficiency`, `converter_efficiency`, `max_solar_input_v`, `max_solar_input_a`, `battery_config`, `num_solar_inputs`, `max_output_channels`, `mass_g`.

### `PowerBus`

```python
bus = PowerBus(bus_voltage=3.3, converter=None)
bus.net_battery_current(solar_power, load_power, battery_voltage) -> float
```

### `DcDcConverter`

```python
conv = DcDcConverter(efficiency=0.92, name="")
conv.output_power(input_power) -> float
conv.input_power(output_power) -> float
```

---

## `satpower.simulation`

### `Simulation`

```python
sim = Simulation(
    orbit, panels, battery, loads,
    environment=None,
    bus=None,
    mppt_efficiency=0.97,
    initial_soc=1.0,
    epoch_day_of_year=80.0,
    eps_board=None,          # overrides bus + mppt_efficiency
)
sim.run(duration_orbits=None, duration_s=None, dt_max=30.0, method="RK45") -> SimulationResults
```

### `SimulationResults`

Arrays: `time`, `soc`, `power_generated`, `power_consumed`, `battery_voltage`, `eclipse`, `modes`.

Properties: `time_minutes`, `time_hours`, `time_orbits`, `worst_case_dod`, `power_margin`, `energy_balance_per_orbit`, `eclipse_fraction`.

Methods:
```python
results.summary() -> dict
results.report(loads, battery, mission_name="Mission") -> PowerBudgetReport
results.plot_soc(ax=None) -> Figure
results.plot_power_balance(ax=None) -> Figure
results.plot_battery_voltage(ax=None) -> Figure
```

### `PowerBudgetReport`

```python
report.to_text() -> str   # human-readable table
report.to_dict() -> dict   # machine-readable
```

Fields: `mission_name`, `subsystems`, `avg_generated_w`, `avg_consumed_w`, `power_margin_w`, `eclipse_fraction`, `worst_dod`, `min_soc`, `battery_energy_wh`, `verdict`.

---

## `satpower.mission`

### `load_mission`

```python
from satpower.mission import load_mission, build_simulation

config = load_mission("path/to/mission.yaml") -> MissionConfig
sim = build_simulation(config) -> Simulation
```

### `MissionConfig`

Pydantic model: `name`, `application`, `orbit` (OrbitConfig), `satellite` (SatelliteConfig), `loads` (list[LoadConfig]), `simulation` (SimulationConfig).

---

## `satpower.validation`

```python
from satpower.validation import validate_system, ValidationResult

result = validate_system(eps, battery, panels, loads_peak_power=None) -> ValidationResult
result.passed    # bool
result.errors    # list[str]
result.warnings  # list[str]
```

---

## `satpower.data`

```python
from satpower.data import registry

registry.list_solar_cells() -> list[str]
registry.list_battery_cells() -> list[str]
registry.list_eps() -> list[str]
registry.list_missions() -> list[str]

registry.get_solar_cell(name) -> SolarCellData
registry.get_battery_cell(name) -> BatteryCellData
registry.get_eps(name) -> EPSData
```
