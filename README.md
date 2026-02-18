# satpower

CubeSat Electrical Power System Simulation Library.

Physics-based simulation connecting orbital mechanics to subsystem-level power analysis. Answer the critical question: *"Will my satellite survive the worst-case eclipse season without running out of power?"*

## Features

- **Orbital mechanics** -- circular LEO propagation with optional J2 perturbation (RAAN drift for SSO fidelity)
- **Eclipse models** -- cylindrical (sharp boundary) or conical (smooth penumbra transitions)
- **Seasonal solar flux** -- accounts for Earth's orbital eccentricity (±3.4% annual variation)
- **Solar cell physics** -- single-diode I-V model with temperature and irradiance dependence
- **Panel geometry** -- body-mounted and deployed wing configurations for 1U/3U/6U CubeSats
- **MPPT modeling** -- constant or power-dependent efficiency (drops at low power)
- **Battery modeling** -- Thevenin R-RC equivalent circuit with Coulomb counting
- **DC-DC converter** -- constant or load-dependent efficiency (peaks mid-load)
- **Thermal dynamics** -- lumped-parameter panel and battery temperature tracking in the ODE
- **Battery aging** -- calendar + cycle fade with Arrhenius temperature acceleration
- **Lifetime simulation** -- multi-segment capacity fade analysis over months/years
- **Component database** -- 6 solar cells, 5 batteries, 4 EPS boards from real datasheets
- **Mission YAML system** -- define missions in YAML, run from CLI or Python
- **Power budget reports** -- margin analysis with verdict
- **SaaS API layer** -- Pydantic request/response models for JSON-based web integration

## Installation

```bash
pip install satpower
```

For development:

```bash
git clone https://github.com/satpower/satpower.git
cd satpower
pip install -e ".[dev]"
```

## Quick Start

```python
import satpower as sp

# Define orbit: 550 km Sun-synchronous with J2 perturbation
orbit = sp.Orbit.circular(altitude_km=550, inclination_deg=97.6, j2=True)

# Define solar panels: 3U CubeSat body-mounted
panels = sp.SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")

# Define battery: 2S2P 18650 pack
battery = sp.BatteryPack.from_cell("panasonic_ncr18650b", config="2S2P")

# Define loads
loads = sp.LoadProfile()
loads.add_mode("idle", power_w=2.0)
loads.add_mode("comms", power_w=8.0, duty_cycle=0.15)
loads.add_mode("payload", power_w=5.0, duty_cycle=0.30)

# Run simulation with conical eclipse model
sim = sp.Simulation(orbit, panels, battery, loads, eclipse_model="conical")
results = sim.run(duration_orbits=5)

# Analyze results
print(results.summary())
results.plot_soc()
results.plot_power_balance()
```

### With thermal modeling

```python
thermal = sp.ThermalModel(sp.ThermalConfig(
    panel_area_m2=sum(p.area_m2 for p in panels),
))

sim = sp.Simulation(
    orbit, panels, battery, loads,
    eclipse_model="conical",
    thermal_model=thermal,
)
results = sim.run(duration_orbits=5)

# Access temperature time series
print(results.panel_temperature)    # K
print(results.battery_temperature)  # K
```

### SaaS API integration

```python
from satpower.api import SimulationRequest, run_simulation_async

@app.post("/api/v1/simulations")
async def create_simulation(request: SimulationRequest):
    return await run_simulation_async(request)
```

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](docs/getting-started.md) | Installation, quick start, first simulation |
| [User Guide](docs/user-guide.md) | Core concepts, advanced physics, building simulations |
| [Physics Models](docs/physics-models.md) | Detailed physics: J2, conical eclipse, thermal, MPPT, aging |
| [Mission Configuration](docs/mission-config.md) | YAML mission files, presets, builder API |
| [SaaS API](docs/saas-api.md) | JSON API layer for web integration |
| [CLI Reference](docs/cli-reference.md) | Command-line tool usage |
| [Component Database](docs/component-database.md) | Available solar cells, batteries, EPS boards |
| [API Reference](docs/api-reference.md) | Module and class reference |
| [Architecture](docs/architecture.md) | Internal design, module structure |

## License

Apache 2.0 -- see [LICENSE](LICENSE) for details.
