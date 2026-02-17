# satpower

CubeSat Electrical Power System Simulation Library.

Physics-based simulation connecting orbital mechanics to subsystem-level power analysis. Answer the critical question: *"Will my satellite survive the worst-case eclipse season without running out of power?"*

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

# Define orbit: 550 km Sun-synchronous
orbit = sp.Orbit.circular(altitude_km=550, inclination_deg=97.6)

# Define solar panels: 3U CubeSat body-mounted
panels = sp.SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")

# Define battery: 2S2P 18650 pack
battery = sp.BatteryPack.from_cell("panasonic_ncr18650b", config="2S2P")

# Define loads
loads = sp.LoadProfile()
loads.add_mode("idle", power_w=2.0)
loads.add_mode("comms", power_w=8.0, duty_cycle=0.15)
loads.add_mode("payload", power_w=5.0, duty_cycle=0.30)

# Run simulation
sim = sp.Simulation(orbit, panels, battery, loads)
results = sim.run(duration_orbits=5)

# Analyze results
print(results.summary())
results.plot_soc()
results.plot_power_balance()
```

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
