# User Guide

## Core concepts

A satpower simulation connects five subsystems:

```
Orbit --> Sun position --> Solar Panels --> EPS Bus --> Battery
                                              ^
                                              |
                                           Loads
```

1. **Orbit** determines satellite position, velocity, and eclipse timing
2. **Solar panels** convert sunlight to electrical power based on geometry and cell physics
3. **EPS board** regulates power through DC-DC converters (MPPT + bus regulation)
4. **Battery** stores and releases energy, modeled with Thevenin equivalent circuit
5. **Loads** consume power with configurable duty cycles and triggers

## Orbits

```python
import satpower as sp

# Circular orbit from altitude and inclination
orbit = sp.Orbit.circular(altitude_km=550, inclination_deg=97.6)

# ISS orbit
iss = sp.Orbit.circular(altitude_km=408, inclination_deg=51.6)

# SSO with J2 perturbation (RAAN precession)
sso = sp.Orbit.circular(altitude_km=550, inclination_deg=97.6, j2=True)

# Access properties
print(orbit.period)        # seconds
print(orbit.altitude_km)   # km
print(orbit.inclination_deg)
```

### J2 perturbation

Earth's oblateness causes the orbital plane to precess. For Sun-synchronous orbits, this produces ~0.9856 deg/day of RAAN drift, matching the Earth's motion around the Sun. Enable J2 for accurate eclipse timing in SSO missions:

```python
orbit = sp.Orbit.circular(altitude_km=550, inclination_deg=97.6, j2=True)
```

### Common CubeSat orbits

| Mission type | Altitude | Inclination | J2 recommended | Notes |
|-------------|----------|-------------|----------------|-------|
| Sun-synchronous (SSO) | 500-700 km | 97-98 deg | Yes | Most common for Earth observation |
| ISS deploy | 408 km | 51.6 deg | Optional | University missions |
| Low-inclination | 500-600 km | 0-45 deg | Optional | IoT/M2M, equatorial coverage |

## Eclipse models

Choose the eclipse model when creating a simulation:

```python
# Cylindrical (default) — binary shadow, no penumbra
sim = sp.Simulation(orbit, panels, battery, loads)

# Conical — smooth penumbra transitions
sim = sp.Simulation(orbit, panels, battery, loads, eclipse_model="conical")
```

The conical model is more realistic, producing slightly shorter full-shadow durations and smoother power transitions at eclipse boundaries.

## Solar panels

### Body-mounted panels

Creates one panel per CubeSat face (6 panels for full body):

```python
panels = sp.SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")
```

Supported form factors: `"1U"`, `"3U"`, `"6U"`.

### Excluding faces

Skip faces occupied by payload, antenna, or docking port:

```python
# Skip nadir face (camera pointing down)
panels = sp.SolarPanel.cubesat_body("3U", "azur_3g30c", exclude_faces=["-Z"])

# Skip top and bottom
panels = sp.SolarPanel.cubesat_body("3U", "azur_3g30c", exclude_faces=["+Z", "-Z"])
```

Face naming convention (nadir-pointing body frame):
- `+X` / `-X` -- ram / anti-ram (along velocity)
- `+Y` / `-Y` -- cross-track (orbit normal)
- `+Z` / `-Z` -- zenith / nadir (nadir = toward Earth)

### Deployed wing panels

Add deployable solar wings for more power:

```python
# Body panels + 2 wings (optimal for SSO)
panels = sp.SolarPanel.cubesat_with_wings(
    "3U", "azur_3g30c",
    wing_count=2,           # 2 or 4
    wing_area_m2=0.06,      # per wing (None = auto: 2x long face)
    exclude_faces=["-Z"],   # skip nadir for camera
)
```

- **2 wings**: normals along +Y/-Y (perpendicular to orbit plane, ideal for SSO)
- **4 wings**: normals along +X/-X and +Y/-Y

### Custom panels

```python
import numpy as np

wing = sp.SolarPanel.deployed(
    area_m2=0.08,
    cell_type="spectrolab_xtj_prime",
    normal=np.array([0, 1, 0]),  # +Y direction
    name="custom_wing",
)
```

## MPPT modeling

By default, MPPT efficiency is a constant (0.97). For more realistic modeling, use power-dependent mode where efficiency drops at low power:

```python
from satpower.solar import MpptModel

mppt = MpptModel(
    efficiency=0.97,
    power_dependent=True,
    rated_power_w=8.0,
    min_efficiency=0.85,
)

sim = sp.Simulation(orbit, panels, battery, loads, mppt_model=mppt)
```

## Batteries

```python
# Create a battery pack from cell name and configuration
battery = sp.BatteryPack.from_cell("panasonic_ncr18650b", config="2S2P")

print(battery.capacity_ah)       # 6.7 Ah (2 parallel)
print(battery.nominal_voltage)   # 7.2 V (2 series)
print(battery.energy_wh)         # 48.2 Wh
```

### Configuration string format

`{series}S{parallel}P` -- e.g., `"2S2P"` means 2 cells in series, 2 in parallel.

- **Series** increases voltage (pack_voltage = cell_voltage x N_series)
- **Parallel** increases capacity (pack_capacity = cell_capacity x N_parallel)

### Common configurations

| Config | Voltage range | Use case |
|--------|--------------|----------|
| `1S1P` | 2.5-4.2V | Very small sats, single-cell |
| `2S1P` | 5.0-8.4V | Standard CubeSat (matches most EPS boards) |
| `2S2P` | 5.0-8.4V | Higher energy, 3U+ missions |
| `2S3P` | 5.0-8.4V | High energy, 6U missions |

## Loads

```python
loads = sp.LoadProfile()

# Always-on subsystem
loads.add_mode("obc", power_w=0.5)

# Duty-cycled load (active 30% of the time)
loads.add_mode("camera", power_w=6.0, duty_cycle=0.30)

# Sunlight-only load (off during eclipse)
loads.add_mode("camera", power_w=6.0, duty_cycle=0.30, trigger="sunlight")

# Eclipse-only load
loads.add_mode("heater", power_w=1.5, trigger="eclipse")

# Comms with 15% duty cycle
loads.add_mode("uhf", power_w=4.0, duty_cycle=0.15, trigger="always")
```

### Trigger types

| Trigger | When active |
|---------|------------|
| `"always"` | Every timestep (default) |
| `"sunlight"` | Only when satellite is in sunlight |
| `"eclipse"` | Only when satellite is in Earth's shadow |

### Subsystem power templates

satpower includes typical power draws for common CubeSat subsystems:

```python
from satpower.loads import SUBSYSTEM_POWER

print(SUBSYSTEM_POWER)
# {'obc_arm': 0.4, 'obc_msp430': 0.15, 'adcs_magnetorquer': 0.8,
#  'adcs_reaction_wheel': 2.5, 'uhf_transceiver': 4.0, ...}
```

## EPS boards

Connect real EPS hardware to the simulation:

```python
eps = sp.EPSBoard.from_datasheet("gomspace_p31u")

print(eps.bus_voltage)           # 3.3 V
print(eps.mppt_efficiency)       # 0.97
print(eps.converter_efficiency)  # 0.92
print(eps.num_solar_inputs)      # 6
print(eps.battery_config)        # "2S1P"

# Use in simulation -- overrides bus and MPPT efficiency
sim = sp.Simulation(orbit, panels, battery, loads, eps_board=eps)
```

When `eps_board` is provided, the simulation automatically uses the EPS board's converter efficiency and MPPT efficiency instead of defaults.

## DC-DC converter

For more realistic power conditioning, use load-dependent converter efficiency:

```python
from satpower.regulation import DcDcConverter, PowerBus

converter = DcDcConverter(
    efficiency=0.92,
    load_dependent=True,
    rated_power_w=15.0,
    peak_efficiency=0.94,
    light_load_efficiency=0.80,
)

bus = PowerBus(bus_voltage=3.3, converter=converter)
sim = sp.Simulation(orbit, panels, battery, loads, bus=bus)
```

## Thermal modeling

Track panel and battery temperatures as part of the ODE state vector:

```python
thermal = sp.ThermalModel(sp.ThermalConfig(
    panel_area_m2=sum(p.area_m2 for p in panels),
    panel_thermal_mass_j_per_k=450.0,
    battery_thermal_mass_j_per_k=95.0,
    spacecraft_interior_temp_k=293.15,
))

sim = sp.Simulation(
    orbit, panels, battery, loads,
    eclipse_model="conical",
    thermal_model=thermal,
)
results = sim.run(duration_orbits=5)

# Temperature time series (Kelvin)
print(results.panel_temperature)
print(results.battery_temperature)
```

Thermal effects feed back into the simulation:
- Panel temperature affects solar cell voltage and current
- Battery temperature affects internal resistance (Arrhenius)

## Running simulations

```python
sim = sp.Simulation(
    orbit=orbit,
    panels=panels,
    battery=battery,
    loads=loads,
    eps_board=eps,              # optional: real EPS board
    initial_soc=1.0,           # starting battery charge (0-1)
    epoch_day_of_year=80.0,    # day of year at simulation start
    eclipse_model="conical",   # or "cylindrical" (default)
    mppt_model=mppt,           # optional: power-dependent MPPT
    thermal_model=thermal,     # optional: temperature tracking
)

results = sim.run(
    duration_orbits=10,   # or duration_s=36000
    dt_max=30.0,          # max timestep (seconds)
)
```

### Results

```python
# Summary statistics
results.summary()

# Key properties
results.worst_case_dod      # max depth of discharge
results.power_margin        # avg generated - consumed (W)
results.eclipse_fraction    # fraction of time in eclipse

# Time-series arrays
results.time                # seconds
results.soc                 # state of charge [0, 1]
results.power_generated     # watts
results.power_consumed      # watts
results.battery_voltage     # volts
results.eclipse             # boolean
results.panel_temperature   # Kelvin (None if thermal disabled)
results.battery_temperature # Kelvin (None if thermal disabled)

# Plots
results.plot_soc()
results.plot_power_balance()
results.plot_battery_voltage()
```

### Power budget report

```python
report = results.report(loads, battery, mission_name="MyMission")
print(report.to_text())    # formatted table
report.to_dict()           # machine-readable
```

## Battery aging

Model long-term capacity fade with Arrhenius temperature acceleration:

```python
from satpower.battery import AgingModel

aging = AgingModel(
    calendar_fade_per_year=0.02,
    cycle_fade_per_cycle_50dod=0.0001,
    cycle_fade_per_cycle_100dod=0.0005,
    reference_temp_k=298.15,
    activation_energy_j=50000.0,
)

remaining = aging.capacity_remaining(
    years=2.0, n_cycles=10000, avg_dod=0.3, temperature_k=308.15
)
print(f"Capacity: {remaining:.1%}")
```

### Lifetime simulation

Run multi-segment simulations over months or years:

```python
from satpower.simulation import LifetimeSimulation

lifetime = LifetimeSimulation(simulation=sim, aging_model=aging)
results = lifetime.run(duration_years=2.0, update_interval_orbits=100)

print(results.capacity_remaining)  # capacity fade over time
```

## Component validation

Check that your components are compatible before running:

```python
from satpower.validation import validate_system

result = validate_system(eps, battery, panels, loads_peak_power=15.0)

print(result.passed)     # True/False
print(result.errors)     # critical issues
print(result.warnings)   # non-critical concerns
```

Checks performed:
1. Battery series count vs EPS design
2. Solar cell Voc vs EPS max solar input voltage
3. Panel Isc vs EPS max solar input current
4. Number of panels vs EPS solar inputs
5. Load power vs estimated generation capacity

## Full physics example

A simulation using all physics features together:

```python
import satpower as sp
from satpower.solar import MpptModel
from satpower.regulation import DcDcConverter, PowerBus

# Orbit with J2 perturbation
orbit = sp.Orbit.circular(altitude_km=550, inclination_deg=97.6, j2=True)

# Panels
panels = sp.SolarPanel.cubesat_body("3U", "azur_3g30c", exclude_faces=["-Z"])

# Battery
battery = sp.BatteryPack.from_cell("panasonic_ncr18650b", "2S2P")

# Loads
loads = sp.LoadProfile()
loads.add_mode("obc", power_w=0.4)
loads.add_mode("adcs", power_w=0.8)
loads.add_mode("camera", power_w=6.0, duty_cycle=0.3, trigger="sunlight")
loads.add_mode("comms", power_w=4.0, duty_cycle=0.15)

# Power-dependent MPPT
mppt = MpptModel(efficiency=0.97, power_dependent=True, rated_power_w=8.0, min_efficiency=0.85)

# Load-dependent converter
converter = DcDcConverter(
    efficiency=0.92, load_dependent=True,
    rated_power_w=15.0, peak_efficiency=0.94, light_load_efficiency=0.80,
)
bus = PowerBus(bus_voltage=3.3, converter=converter)

# Thermal model
thermal = sp.ThermalModel(sp.ThermalConfig(
    panel_area_m2=sum(p.area_m2 for p in panels),
))

# Run with all physics
sim = sp.Simulation(
    orbit, panels, battery, loads,
    bus=bus, mppt_model=mppt,
    eclipse_model="conical",
    thermal_model=thermal,
    epoch_day_of_year=80.0,
)
results = sim.run(duration_orbits=5, dt_max=60.0)

print(results.summary())
```
