# satpower Documentation

**CubeSat Electrical Power System Simulation Library**

Physics-based simulation connecting orbital mechanics to subsystem-level power analysis. Answer the critical question: *"Will my satellite survive the worst-case eclipse season without running out of power?"*

## What satpower does

- Simulates solar power generation across all CubeSat body faces and deployed wings
- Models battery charge/discharge with Thevenin R-RC equivalent circuit
- Tracks state of charge through eclipse/sunlight cycles using ODE integration
- Supports J2 orbit perturbation for Sun-synchronous orbit fidelity
- Models conical eclipse with smooth penumbra transitions
- Tracks panel and battery temperatures as part of the ODE state vector
- Models power-dependent MPPT and load-dependent converter efficiency
- Simulates battery aging with Arrhenius temperature acceleration
- Validates component compatibility (EPS, battery, panels)
- Generates power budget reports with margin analysis
- Ships with real component datasheets (solar cells, batteries, EPS boards)
- Provides a CLI for running mission simulations from YAML files
- Includes a SaaS API layer for JSON-based web integration

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](getting-started.md) | Installation, quick start, first simulation |
| [User Guide](user-guide.md) | Core concepts, advanced physics, building simulations |
| [Physics Models](physics-models.md) | Detailed physics: J2, conical eclipse, thermal, MPPT, aging |
| [Mission Configuration](mission-config.md) | YAML mission files, presets, builder API |
| [SaaS API](saas-api.md) | JSON API layer for web integration |
| [CLI Reference](cli-reference.md) | Command-line tool usage |
| [Component Database](component-database.md) | Available solar cells, batteries, EPS boards |
| [API Reference](api-reference.md) | Module and class reference |
| [Architecture](architecture.md) | Internal design, module structure, physics models |

## Quick example

```bash
# Run a bundled mission preset
satpower run earth_observation_3u.yaml

# List available components
satpower list cells
satpower list batteries
satpower list eps
```

```python
import satpower as sp

orbit = sp.Orbit.circular(altitude_km=550, inclination_deg=97.6, j2=True)
panels = sp.SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")
battery = sp.BatteryPack.from_cell("panasonic_ncr18650b", config="2S2P")

loads = sp.LoadProfile()
loads.add_mode("idle", power_w=2.0)
loads.add_mode("comms", power_w=8.0, duty_cycle=0.15)
loads.add_mode("payload", power_w=5.0, duty_cycle=0.30)

sim = sp.Simulation(orbit, panels, battery, loads, eclipse_model="conical")
results = sim.run(duration_orbits=5)
print(results.summary())
```
