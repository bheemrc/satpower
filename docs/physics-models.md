# Physics Models

Detailed documentation for the physics models in satpower.

## Orbital mechanics

### Kepler propagation

Analytical propagation for circular orbits. The satellite starts at the ascending node at t=0 and follows a constant-altitude trajectory. Position and velocity are computed in the ECI (Earth-Centered Inertial) frame.

### J2 perturbation

Optional secular perturbation from Earth's oblateness (J2 = 1.08263e-3). When enabled, the Right Ascension of the Ascending Node (RAAN) precesses at:

```
dΩ/dt = -1.5 * n * J2 * (R_E / a)² * cos(i)
```

Where:
- `n` = mean motion (rad/s)
- `R_E` = Earth's equatorial radius (6378.137 km)
- `a` = semi-major axis
- `i` = orbital inclination

For Sun-synchronous orbits (SSO), this produces ~0.9856 deg/day of RAAN precession, matching the Earth's orbital motion around the Sun. This is critical for accurate eclipse timing over long durations.

```python
# Enable J2 perturbation
orbit = sp.Orbit.circular(altitude_km=550, inclination_deg=97.6, j2=True)
```

Key behaviors:
- **SSO (i~97.6 deg):** RAAN drifts ~0.9856 deg/day (tracks Sun)
- **Polar (i=90 deg):** Zero RAAN drift (cos(90) = 0)
- **Equatorial (i=0 deg):** Maximum RAAN drift rate
- **Disabled by default** for backwards compatibility

## Eclipse models

### Cylindrical (default)

Earth's shadow is modeled as an infinite cylinder aligned with the Sun direction. Shadow fraction is binary: 0 (sunlit) or 1 (eclipse). No penumbra.

Sufficient for power budgets where sharp eclipse transitions are acceptable.

### Conical

Models the Sun as a finite disk, producing smooth penumbra transitions at eclipse boundaries. Uses angular overlap between the Sun and Earth disks as seen from the satellite:

```
theta_sun   = arcsin(R_SUN / d_sat_to_sun)     # ~0.265 deg from LEO
theta_earth = arcsin(R_EARTH / d_sat_to_earth)  # ~60 deg from LEO
theta_sep   = angle between Earth center and Sun center from satellite
```

Shadow regions:
- **Full sun** (`theta_sep >= theta_earth + theta_sun`): shadow = 0.0
- **Penumbra** (partial overlap): linear ramp between 0 and 1
- **Full umbra** (`theta_sep <= theta_earth - theta_sun`): shadow = 1.0

```python
# Use conical eclipse model
sim = sp.Simulation(orbit, panels, battery, loads, eclipse_model="conical")
```

The conical model produces slightly shorter full-shadow durations and smoother power transitions, which is more realistic for solar power predictions.

## Seasonal solar flux

The solar constant varies by ±3.4% over the year due to Earth's orbital eccentricity. satpower models this as:

```
flux(doy) = 1361 * (1 + 0.0334 * cos(2π * (doy - 3) / 365.25))
```

Where `doy` is the day of year. Key values:
- **Perihelion** (day ~3, January): flux ~ 1407 W/m²
- **Aphelion** (day ~186, July): flux ~ 1316 W/m²
- **Annual average**: ~1361 W/m²

This is always enabled (negligible computational cost, strictly more accurate than a constant).

## Solar cell model

Single-diode equivalent circuit:

```
I = I_ph - I_0 * [exp((V + I*R_s) / V_t) - 1] - (V + I*R_s) / R_sh
```

- **I_ph** (photocurrent): scales linearly with irradiance, adjusts with temperature
- **I_0** (saturation current): Arrhenius temperature dependence
- **V_t** (thermal voltage): `n * k_B * T / q`
- **R_s, R_sh**: series and shunt resistance from datasheet

Maximum power point uses a fill-factor approximation:

```
FF = (v_oc_norm - ln(v_oc_norm + 0.72)) / (v_oc_norm + 1)
P_mpp = I_sc * V_oc * FF * (1 - R_s * I_sc / V_oc)
```

## MPPT power-dependent efficiency

The MPPT tracker efficiency can optionally vary with input power level. At low power (e.g., grazing sun angles), the tracker operates less efficiently.

Model:

```
η = η_peak - (η_peak - η_min) * exp(-5 * P / P_rated)
```

Where:
- `η_peak` = peak efficiency (default 0.97)
- `η_min` = minimum efficiency at very low power (default 0.85)
- `P` = current panel power
- `P_rated` = rated MPPT power (default 10 W)

```python
from satpower.solar import MpptModel

mppt = MpptModel(
    efficiency=0.97,          # peak efficiency
    power_dependent=True,
    rated_power_w=8.0,        # rated power for your panels
    min_efficiency=0.85,      # efficiency at very low power
)

sim = sp.Simulation(orbit, panels, battery, loads, mppt_model=mppt)
```

Key behaviors:
- At rated power: efficiency approaches `η_peak`
- At 10% of rated: efficiency ~0.92 (significant drop)
- At zero power: efficiency = `η_min`
- **Disabled by default** (constant efficiency)

## DC-DC converter load-dependent efficiency

The converter efficiency can optionally vary with output load level, modeling real converter behavior where switching losses dominate at light loads and conduction losses cause droop at heavy loads.

Model characteristics:
- **Light load (<10% rated):** Low efficiency (switching losses dominate)
- **Mid load (~50% rated):** Peak efficiency
- **Heavy load (>80% rated):** Mild efficiency droop (conduction losses)

```python
from satpower.regulation import DcDcConverter

converter = DcDcConverter(
    efficiency=0.92,
    load_dependent=True,
    rated_power_w=15.0,
    peak_efficiency=0.94,
    light_load_efficiency=0.80,
)

bus = sp.PowerBus(bus_voltage=3.3, converter=converter)
sim = sp.Simulation(orbit, panels, battery, loads, bus=bus)
```

Key behaviors:
- Peak efficiency at ~50% of rated load
- Efficiency drops at both very light and very heavy loads
- **Disabled by default** (constant efficiency)

## Thermal model

Lumped-parameter thermal model tracking panel and battery temperatures as part of the ODE state vector.

### Panel thermal dynamics

The panel temperature evolves based on absorbed solar radiation, Earth albedo, Earth IR, and radiative cooling to space:

```
dT_panel/dt = (Q_solar + Q_albedo + Q_earth_ir - Q_radiated) / (m * Cp)
```

Where:
- `Q_solar` = absorbed solar power not converted to electricity (W)
- `Q_albedo` = α * F_albedo * A_panel (W)
- `Q_earth_ir` = ε * F_earth_ir * A_panel (W)
- `Q_radiated` = ε * σ * A_panel * 2 * T⁴ (radiates from both sides)
- `σ` = Stefan-Boltzmann constant (5.67e-8 W/m²/K⁴)

Typical equilibrium temperatures:
- **Sunlit:** 300-340 K (27-67 C)
- **Eclipse:** cools toward ~200 K

### Battery thermal dynamics

The battery temperature is driven by internal Joule heating (I²R) and radiative exchange with the spacecraft interior:

```
dT_battery/dt = (I²R + P_heater - ε * σ * A_bat * (T_bat⁴ - T_sc⁴)) / (m * Cp)
```

Where:
- `I²R` = Joule heating from battery current and internal resistance
- `P_heater` = survival heater power (optional)
- `T_sc` = spacecraft interior temperature (default 293.15 K / 20 C)

### Usage

```python
thermal = sp.ThermalModel(sp.ThermalConfig(
    panel_area_m2=sum(p.area_m2 for p in panels),
    panel_thermal_mass_j_per_k=450.0,    # 0.5 kg * 900 J/(kg·K)
    battery_thermal_mass_j_per_k=95.0,
    spacecraft_interior_temp_k=293.15,   # 20 C
))

sim = sp.Simulation(
    orbit, panels, battery, loads,
    eclipse_model="conical",
    thermal_model=thermal,
)
results = sim.run(duration_orbits=5)

# Temperature time series (Kelvin)
results.panel_temperature
results.battery_temperature
```

### State vector

When thermal modeling is enabled, the ODE state vector expands from 3 to 5 components:

| Index | Variable | Description |
|-------|----------|-------------|
| 0 | SoC | Battery state of charge |
| 1 | V_rc1 | RC circuit voltage 1 |
| 2 | V_rc2 | RC circuit voltage 2 |
| 3 | T_panel | Panel temperature (K) |
| 4 | T_battery | Battery temperature (K) |

When disabled, the simulation uses constant default temperatures (panel 28 C, battery 25 C).

### Thermal feedback

Temperature affects the simulation through:
- **Solar cell power output:** Cell voltage and current shift with temperature
- **Battery internal resistance:** Arrhenius temperature dependence of R0
- **Battery OCV:** Temperature-dependent open-circuit voltage

## Battery aging

### Calendar and cycle fade

The `AgingModel` combines calendar aging (time-based) and cycle aging (use-based):

```
capacity_remaining = 1.0 - calendar_loss - cycle_loss
```

- **Calendar loss:** `fade_per_year * years * arrhenius_factor`
- **Cycle loss:** `fade_per_cycle(DoD) * n_cycles * arrhenius_factor`

Cycle fade is interpolated between 50% and 100% DoD reference values from the battery datasheet.

### Arrhenius temperature acceleration

Battery aging accelerates at elevated temperatures following the Arrhenius equation:

```
factor = exp(Ea/R * (1/T_ref - 1/T))
```

Where:
- `Ea` = activation energy (default 50,000 J/mol)
- `R` = universal gas constant (8.314 J/(mol·K))
- `T_ref` = reference temperature (default 298.15 K / 25 C)

Key values:
- At 25 C (reference): factor = 1.0
- At 35 C: factor ~ 2.0 (aging doubles)
- At 45 C: factor ~ 3.6 (aging triples)
- At 15 C: factor ~ 0.5 (aging halved)

```python
from satpower.battery import AgingModel

aging = AgingModel(
    calendar_fade_per_year=0.02,         # 2% per year at 25 C
    cycle_fade_per_cycle_50dod=0.0001,
    cycle_fade_per_cycle_100dod=0.0005,
    reference_temp_k=298.15,
    activation_energy_j=50000.0,
)

remaining = aging.capacity_remaining(
    years=2.0,
    n_cycles=10000,
    avg_dod=0.3,
    temperature_k=308.15,  # 35 C — accelerated aging
)
```

## Lifetime simulation

The `LifetimeSimulation` class runs multi-segment simulations over months or years, updating battery capacity between segments. This avoids adding aging to the ODE (timescale mismatch: aging operates on months, the ODE on seconds).

```python
from satpower.simulation import LifetimeSimulation
from satpower.battery import AgingModel

aging = AgingModel()
lifetime = LifetimeSimulation(simulation=sim, aging_model=aging)
results = lifetime.run(
    duration_years=2.0,
    update_interval_orbits=100,
    orbits_per_segment=3,
)

# Results
results.segment_years          # time points (years)
results.capacity_remaining     # fraction of original capacity
results.min_soc_per_segment    # worst SoC per segment
results.worst_dod_per_segment  # worst DoD per segment
```
