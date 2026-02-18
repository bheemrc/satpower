# Architecture

## Module structure

```
src/satpower/
├── __init__.py            # Top-level exports
├── __main__.py            # CLI entry point
├── _version.py            # Version string
│
├── orbit/                 # Orbital mechanics
│   ├── _propagator.py     # Kepler propagation + J2 perturbation
│   ├── _eclipse.py        # Cylindrical + conical shadow models
│   ├── _environment.py    # Solar flux (seasonal), albedo, Earth IR
│   └── _geometry.py       # Sun vector, incidence angles
│
├── solar/                 # Solar power generation
│   ├── _cell.py           # Single-diode I-V model
│   ├── _panel.py          # Panel geometry (body, wings)
│   ├── _mppt.py           # MPPT efficiency (constant + power-dependent)
│   └── _degradation.py    # Radiation degradation
│
├── battery/               # Energy storage
│   ├── _cell.py           # Thevenin R-RC model
│   ├── _pack.py           # Series/parallel packs
│   ├── _soc.py            # Coulomb counting
│   └── _aging.py          # Calendar + cycle aging (Arrhenius)
│
├── loads/                 # Power consumption
│   ├── _profile.py        # Load modes, duty cycles
│   ├── _scheduler.py      # Mode transitions
│   └── _templates.py      # Standard power draws
│
├── regulation/            # Power conditioning
│   ├── _converter.py      # DC-DC converter (constant + load-dependent)
│   ├── _bus.py            # Power bus regulation
│   └── _eps_board.py      # EPS board abstraction
│
├── thermal/               # Thermal dynamics
│   └── _model.py          # Lumped-parameter panel + battery model
│
├── simulation/            # Simulation engine
│   ├── _engine.py         # ODE integration (solve_ivp)
│   ├── _results.py        # Results container + plots
│   ├── _lifetime.py       # Multi-segment lifetime simulation
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
├── api/                   # SaaS API layer
│   ├── _schemas.py        # Pydantic request/response models
│   ├── _services.py       # Orchestration (run_simulation, etc.)
│   ├── _serializers.py    # NumPy-to-JSON, matplotlib-to-base64
│   └── _errors.py         # Domain-specific exceptions
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
    |    or   [SoC, V_rc1, V_rc2,        |
    |          T_panel, T_battery]        |
    |                                    |
    |  Each timestep:                    |
    |   1. Propagate orbit (+ J2 drift)  |
    |   2. Compute Sun position          |
    |   3. Check eclipse (cyl/conical)   |
    |   4. Seasonal solar flux at epoch  |
    |   5. Compute solar power per panel |
    |   6. Apply MPPT (power-dependent)  |
    |   7. Compute load power            |
    |   8. Power bus balance (load-dep)  |
    |   9. Battery current & SoC update  |
    |  10. Thermal derivatives (if on)   |
    +------------------------------------+
                    |
            SimulationResults
                    |
          +---------+----------+
          |         |          |
    summary    plots    PowerBudgetReport
```

### SaaS API data flow

```
    JSON Request (Pydantic)
            |
    SimulationRequest
            |
    run_simulation()  -->  MissionConfig
            |                   |
            |             build_simulation()
            |                   |
            |              Simulation.run()
            |                   |
            |            SimulationResults
            |                   |
    serialize (plots, summary, budget)
            |
    SimulationResponse (Pydantic)
            |
    JSON Response
```

## Physics models

### Orbit propagation

Analytical Kepler propagation for circular orbits. The satellite starts at the ascending node at t=0 and follows a constant-altitude trajectory. Position and velocity are computed in the ECI (Earth-Centered Inertial) frame.

**J2 perturbation** (optional): When enabled, RAAN precesses at `dΩ/dt = -1.5 * n * J2 * (R_E/a)² * cos(i)`. Critical for SSO fidelity over multi-orbit simulations. Disabled by default.

### Eclipse models

- **Cylindrical** (default): binary shadow (0 or 1), no penumbra
- **Conical**: smooth penumbra transitions using angular overlap of Sun and Earth disks

### Seasonal solar flux

Solar constant varies ±3.4% annually due to Earth's orbital eccentricity:
`flux(doy) = 1361 * (1 + 0.0334 * cos(2π * (doy - 3) / 365.25))`

Always enabled (negligible cost).

### Solar cell model

Single-diode equivalent circuit with temperature and irradiance dependence. Fill-factor approximation for maximum power point.

### MPPT model

Constant efficiency (default 0.97) or power-dependent mode where efficiency drops exponentially at low panel power: `η = η_peak - (η_peak - η_min) * exp(-5 * P/P_rated)`.

### DC-DC converter model

Constant efficiency (default 0.92) or load-dependent mode with:
- Low efficiency at light loads (switching losses)
- Peak efficiency at ~50% rated load
- Mild droop above ~80% rated load (conduction losses)

### Thermal model

Lumped-parameter model tracking panel and battery temperatures in the ODE state vector:
- **Panel**: absorbed solar + albedo + Earth IR - Stefan-Boltzmann radiation (both sides)
- **Battery**: Joule heating (I²R) + heater - radiation to spacecraft interior

### Battery model

2nd-order Thevenin equivalent circuit with OCV(SoC), R0 (Arrhenius temperature dependence), and two R-C time constants.

### Battery aging

Calendar + cycle fade with Arrhenius temperature acceleration. Separate `LifetimeSimulation` class for multi-year capacity fade analysis.

### Panel geometry

Body frame convention (nadir-pointing):
- **Z_body**: toward Earth (nadir)
- **X_body**: along velocity (ram)
- **Y_body**: completes right-hand frame (cross-track)

Panel power = cell_power(irradiance, temperature) * n_cells * mppt_efficiency.

### Power bus

Power balance determines battery current:
- **Sunlit**: solar through MPPT to bus; excess charges battery
- **Eclipse**: battery supplies all loads through converter

Converter efficiency is constant or load-dependent.

## ODE integration

The simulation uses `scipy.integrate.solve_ivp` with the RK45 method.

**Standard state vector** (3 components): `[SoC, V_rc1, V_rc2]`

**Thermal state vector** (5 components): `[SoC, V_rc1, V_rc2, T_panel, T_battery]`

At each timestep, the right-hand side function:

1. Propagates the orbit (with optional J2 RAAN drift)
2. Computes Sun position (simplified annual motion in ecliptic)
3. Determines shadow fraction (cylindrical or conical)
4. Computes seasonal solar flux at current day-of-year
5. Computes solar power from all panels (body frame transform, dynamic temperature)
6. Applies MPPT efficiency (constant or power-dependent)
7. Computes load power (trigger-based, duty-cycled)
8. Solves power bus balance for battery current (load-dependent converter)
9. Computes battery state derivatives (SoC, RC voltages)
10. Computes thermal derivatives if enabled (panel + battery temperatures)

After integration, auxiliary quantities (power, voltage, eclipse state, temperatures) are recomputed at each output timestep.

## Testing strategy

Tests are organized to mirror the source structure:

```
tests/
├── conftest.py              # Shared fixtures
├── test_api/                # API schemas, services, serializers
├── test_battery/            # Cell, pack, aging (Arrhenius), SoC tests
├── test_data/               # Registry and YAML loading
├── test_integration/        # Full physics integration tests
├── test_loads/              # Load profiles, scheduling
├── test_mission/            # Config parsing, all 5 scenario runs
├── test_orbit/              # Propagation (J2), eclipse (conical), environment (seasonal)
├── test_regulation/         # Converter (load-dependent), bus, EPS board
├── test_simulation/         # Engine integration, results, lifetime
├── test_solar/              # Cell I-V, panel geometry, MPPT, degradation
├── test_thermal/            # Panel + battery thermal model
└── test_validation/         # Compatibility checks, reference missions
```

284 tests total. The integration tests run all physics features together (J2 + conical + thermal + power-dependent MPPT + load-dependent converter) and verify physically reasonable results.
