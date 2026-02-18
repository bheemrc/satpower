# Getting Started

> **Usage note:** satpower is a development-stage library. Models are based on published physics and component datasheets, but have not been validated against real satellite telemetry or in-orbit power data. Always independently verify results before relying on them for mission-critical decisions.

## Installation

```bash
pip install satpower
```

For development:

```bash
git clone https://github.com/bheemrc/satpower.git
cd satpower
pip install -e ".[dev]"
```

### Requirements

- Python 3.10+
- numpy, scipy, pydantic, pyyaml, matplotlib

## Your first simulation

### Option 1: YAML mission file (easiest)

Create a file called `my_mission.yaml`:

```yaml
name: "My First CubeSat"
application: "tech_demo"
orbit:
  altitude_km: 550
  inclination_deg: 97.6
satellite:
  form_factor: "3U"
  eps_board: "gomspace_p31u"
  solar:
    cell: "azur_3g30c"
    body_panels: true
  battery:
    cell: "panasonic_ncr18650b"
    config: "2S2P"
loads:
  - name: obc
    power_w: 0.5
  - name: radio
    power_w: 4.0
    duty_cycle: 0.15
  - name: payload
    power_w: 5.0
    duty_cycle: 0.30
simulation:
  duration_orbits: 5
```

Run it:

```bash
satpower run my_mission.yaml
```

Output:

```
============================================================
  POWER BUDGET REPORT: My First CubeSat
============================================================

  SUBSYSTEM BREAKDOWN
  Subsystem                  Power (W)     Duty    Trigger
  obc                             0.50     100%     always
  radio                           4.00      15%     always
  payload                         5.00      30%     always

  ORBIT AVERAGES
    Eclipse fraction:  37.5%
    Generated:        4.15 W
    Consumed (sun):    2.60 W
    Consumed (ecl):    2.60 W
    Consumed (avg):    2.60 W
    Margin:        +  1.55 W

  BATTERY
    Worst DoD:        2.8%
    Min SoC:         97.2%
    Pack energy:      48.2 Wh
    Sizing margin:   35.7x

  VERDICT: POSITIVE MARGIN
============================================================
```

### Option 2: Use a bundled preset

satpower ships with 5 ready-to-run mission presets:

```bash
# List them
satpower list missions

# Run one
satpower run earth_observation_3u.yaml
```

### Option 3: Python API

```python
import satpower as sp

# 1. Define the orbit
orbit = sp.Orbit.circular(altitude_km=550, inclination_deg=97.6)

# 2. Define solar panels
panels = sp.SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")

# 3. Define the battery
battery = sp.BatteryPack.from_cell("panasonic_ncr18650b", config="2S2P")

# 4. Define power loads
loads = sp.LoadProfile()
loads.add_mode("idle", power_w=2.0)
loads.add_mode("comms", power_w=8.0, duty_cycle=0.15)
loads.add_mode("payload", power_w=5.0, duty_cycle=0.30)

# 5. Run the simulation
sim = sp.Simulation(orbit, panels, battery, loads)
results = sim.run(duration_orbits=5)

# 6. Inspect results
print(results.summary())
results.plot_soc()
results.plot_power_balance()
```

## Understanding the output

Key metrics from `results.summary()`:

| Metric | What it means |
|--------|---------------|
| `min_soc` | Lowest battery state of charge (1.0 = full, 0.0 = empty) |
| `worst_case_dod` | Maximum depth of discharge (lower is better, <50% recommended) |
| `power_margin_w` | Average generated minus consumed (positive = surplus) |
| `eclipse_fraction` | Fraction of orbit spent in Earth's shadow (typically 30-40% for LEO) |
| `energy_balance_per_orbit_wh` | Net energy per orbit (positive = battery recovers each orbit) |

### What makes a healthy power budget?

- **Positive power margin** -- the satellite generates more than it consumes on average
- **DoD < 50%** -- battery doesn't discharge too deeply (extends cycle life)
- **Energy balance > 0** -- battery fully recovers each orbit

## Next steps

- [User Guide](user-guide.md) -- learn about EPS boards, deployed panels, load triggers, advanced physics
- [Physics Models](physics-models.md) -- J2 perturbation, conical eclipse, thermal, MPPT, aging
- [Mission Configuration](mission-config.md) -- YAML format reference
- [SaaS API](saas-api.md) -- JSON API layer for web integration
- [Component Database](component-database.md) -- browse available parts
