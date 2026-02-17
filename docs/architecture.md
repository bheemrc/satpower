# Architecture

## Module structure

```
src/satpower/
├── __init__.py            # Top-level exports
├── __main__.py            # CLI entry point
├── _version.py            # Version string
│
├── orbit/                 # Orbital mechanics
│   ├── _propagator.py     # Kepler orbit propagation
│   ├── _eclipse.py        # Cylindrical shadow model
│   ├── _environment.py    # Solar flux, albedo, Earth IR
│   └── _geometry.py       # Sun vector, incidence angles
│
├── solar/                 # Solar power generation
│   ├── _cell.py           # Single-diode I-V model
│   ├── _panel.py          # Panel geometry (body, wings)
│   ├── _mppt.py           # MPPT efficiency model
│   └── _degradation.py    # Radiation degradation
│
├── battery/               # Energy storage
│   ├── _cell.py           # Thevenin R-RC model
│   ├── _pack.py           # Series/parallel packs
│   ├── _soc.py            # Coulomb counting
│   └── _aging.py          # Calendar + cycle aging
│
├── loads/                 # Power consumption
│   ├── _profile.py        # Load modes, duty cycles
│   ├── _scheduler.py      # Mode transitions
│   └── _templates.py      # Standard power draws
│
├── regulation/            # Power conditioning
│   ├── _converter.py      # DC-DC converter model
│   ├── _bus.py            # Power bus regulation
│   └── _eps_board.py      # EPS board abstraction
│
├── simulation/            # Simulation engine
│   ├── _engine.py         # ODE integration (solve_ivp)
│   ├── _results.py        # Results container + plots
│   ├── _events.py         # Eclipse event detection
│   ├── _report.py         # Power budget report
│   └── _montecarlo.py     # Monte Carlo (placeholder)
│
├── mission/               # Mission configuration
│   ├── _config.py         # Pydantic models
│   └── _builder.py        # YAML -> Simulation builder
│
├── validation/            # Compatibility checks
│   └── _checks.py         # System validation
│
└── data/                  # Component database
    ├── _loader.py         # YAML parsing + Pydantic models
    ├── _registry.py       # Component auto-discovery
    ├── cells/             # Solar cell datasheets (.yaml)
    ├── batteries/         # Battery cell datasheets (.yaml)
    ├── eps/               # EPS board profiles (.yaml)
    └── missions/          # Mission preset files (.yaml)
```

## Data flow

```
                    Mission YAML
                        |
                   load_mission()
                        |
                   build_simulation()
                        |
            +-----------+-----------+
            |           |           |
          Orbit      Panels      Battery
            |           |           |
            v           v           v
    +-------+----+------+----+-----+----+
    |            Simulation              |
    |  (ODE integration via solve_ivp)   |
    |                                    |
    |  State: [SoC, V_rc1, V_rc2]        |
    |                                    |
    |  Each timestep:                    |
    |   1. Propagate orbit position      |
    |   2. Compute Sun position          |
    |   3. Check eclipse (shadow model)  |
    |   4. Compute solar power per panel |
    |   5. Compute load power            |
    |   6. Power bus balance             |
    |   7. Battery current & SoC update  |
    +------------------------------------+
                    |
            SimulationResults
                    |
          +---------+----------+
          |                    |
    summary/plots     PowerBudgetReport
```

## Physics models

### Orbit propagation

Analytical Kepler propagation for circular orbits. The satellite starts at the ascending node at t=0 and follows a constant-altitude trajectory. Position and velocity are computed in the ECI (Earth-Centered Inertial) frame.

Limitations: no J2 perturbation, no drag, no RAAN drift. Sufficient for power budget analysis where eclipse timing is the primary concern.

### Solar cell model

Single-diode equivalent circuit:

```
I = I_ph - I_0 * [exp((V + I*R_s) / V_t) - 1] - (V + I*R_s) / R_sh
```

- **I_ph** (photocurrent): scales linearly with irradiance, adjusts with temperature
- **I_0** (saturation current): Arrhenius temperature dependence
- **V_t** (thermal voltage): `n * k_B * T / q`
- **R_s, R_sh**: series and shunt resistance from datasheet

Maximum power point uses a fill-factor approximation for performance:

```
FF = (v_oc_norm - ln(v_oc_norm + 0.72)) / (v_oc_norm + 1)
P_mpp = I_sc * V_oc * FF * (1 - R_s * I_sc / V_oc)
```

### Eclipse model

Cylindrical shadow model: Earth's shadow is a cylinder aligned with the Sun direction. No penumbra modeling (sufficient for power budgets). Shadow fraction is binary: 0 (sunlit) or 1 (eclipse).

### Panel geometry

Body frame convention (nadir-pointing):
- **Z_body**: toward Earth (nadir)
- **X_body**: along velocity (ram)
- **Y_body**: completes right-hand frame (cross-track)

Panel power = cell_power(effective_irradiance) * n_cells * mppt_efficiency, where effective_irradiance = irradiance * cos(incidence_angle), and panels facing away from the Sun produce zero power.

### Battery model

2nd-order Thevenin equivalent circuit:

```
V_terminal = OCV(SoC) - I * R0 - V_rc1 - V_rc2

dV_rc1/dt = I/C1 - V_rc1/(R1*C1)
dV_rc2/dt = I/C2 - V_rc2/(R2*C2)
```

OCV is interpolated from a SoC lookup table. R0 has Arrhenius temperature dependence. State of charge evolves via Coulomb counting: `dSoC/dt = -I / (capacity * 3600)`.

### Power bus

Power balance at the bus determines battery current:

- **Sunlit**: solar power passes through MPPT converter to bus. Excess charges battery (with converter loss). Deficit is supplied by battery (with converter loss).
- **Eclipse**: battery supplies all load power through the converter.

```
solar_to_bus = solar_power * converter_efficiency
net_power = load_power - solar_to_bus

if net_power > 0:  # discharging
    battery_power = net_power / converter_efficiency
else:              # charging
    battery_power = net_power * converter_efficiency

battery_current = battery_power / battery_voltage
```

## ODE integration

The simulation uses `scipy.integrate.solve_ivp` with the RK45 method. The state vector is `[SoC, V_rc1, V_rc2]`. At each timestep, the right-hand side function:

1. Propagates the orbit to get satellite position/velocity
2. Computes Sun position (simplified annual motion in ecliptic)
3. Determines shadow fraction
4. Computes solar power from all panels (coordinate transform to body frame)
5. Computes load power (trigger-based, duty-cycled)
6. Solves power bus balance for battery current
7. Returns state derivatives

After integration, auxiliary quantities (power, voltage, eclipse state) are recomputed at each output timestep for the results container.

## Testing strategy

Tests are organized to mirror the source structure:

```
tests/
├── conftest.py              # Shared fixtures
├── test_battery/            # Cell, pack, aging, SoC tests
├── test_data/               # Registry and YAML loading
├── test_loads/              # Load profiles, scheduling
├── test_mission/            # Config parsing, all 5 scenario runs
├── test_orbit/              # Propagation, eclipse, environment
├── test_regulation/         # Converter, bus, EPS board
├── test_simulation/         # Engine integration, results
├── test_solar/              # Cell I-V, panel geometry, degradation
└── test_validation/         # Compatibility checks, reference missions
```

209 tests total. The mission scenario tests run all 5 presets end-to-end and verify positive power margin and reasonable DoD.
