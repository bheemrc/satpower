# Mission Configuration

Missions are defined in YAML files that describe the orbit, satellite hardware, power loads, and simulation parameters. This is the easiest way to use satpower -- no Python code required.

> **Note:** Mission presets ship with representative parameters for common CubeSat configurations. They are starting points for analysis, not validated mission designs. Users should substitute actual hardware specifications and load profiles for their specific mission.

## YAML format

```yaml
name: "EarthMapper-1"
application: "earth_observation"

orbit:
  type: circular              # only "circular" supported
  altitude_km: 550
  inclination_deg: 97.6
  raan_deg: 0.0               # optional, default 0
  j2: true                    # optional, enable J2 perturbation
  eclipse_model: conical      # optional, "cylindrical" (default) or "conical"

satellite:
  form_factor: "3U"           # "1U", "3U", or "6U"
  eps_board: "gomspace_p31u"  # optional, from component database

  solar:
    cell: "azur_3g30c"        # solar cell from database
    body_panels: true         # mount cells on body faces
    exclude_faces: ["-Z"]     # optional, skip faces
    deployed_wings:            # optional
      count: 2                # 2 or 4
      area_m2: 0.06           # per wing, null = auto

  battery:
    cell: "panasonic_ncr18650b"
    config: "2S2P"            # {series}S{parallel}P

loads:
  - name: obc
    power_w: 0.5
  - name: camera
    power_w: 6.0
    duty_cycle: 0.30          # optional, default 1.0
    trigger: sunlight         # optional: always|sunlight|eclipse
  - name: heater
    power_w: 1.5
    trigger: eclipse

simulation:
  duration_orbits: 10         # optional, default 10
  initial_soc: 1.0            # optional, default 1.0
  dt_max: 30.0                # optional, default 30
  thermal:                    # optional, thermal model
    enabled: true
    panel_thermal_mass_j_per_k: 500
    battery_thermal_mass_j_per_k: 95
    spacecraft_interior_temp_k: 293.15
```

## Field reference

### `orbit`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | string | no | `"circular"` | Orbit type (only circular supported) |
| `altitude_km` | float | yes | -- | Orbital altitude in km |
| `inclination_deg` | float | yes | -- | Orbital inclination in degrees |
| `raan_deg` | float | no | `0.0` | Right Ascension of Ascending Node |
| `j2` | bool | no | `false` | Enable J2 perturbation (RAAN drift) |
| `eclipse_model` | string | no | `"cylindrical"` | Eclipse model: `"cylindrical"` or `"conical"` |

### `satellite`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `form_factor` | string | no | `"3U"` | CubeSat size: `"1U"`, `"3U"`, `"6U"` |
| `eps_board` | string | no | `null` | EPS board name from database |

### `satellite.solar`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `cell` | string | yes | -- | Solar cell name from database |
| `body_panels` | bool | no | `true` | Mount cells on body faces |
| `exclude_faces` | list | no | `null` | Faces to skip: `"+X"`, `"-X"`, `"+Y"`, `"-Y"`, `"+Z"`, `"-Z"` |

### `satellite.solar.deployed_wings`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `count` | int | no | `2` | Number of wings: 2 or 4 |
| `area_m2` | float | no | auto | Area per wing in m^2. Auto = 2x long face area |

### `satellite.battery`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `cell` | string | yes | -- | Battery cell name from database |
| `config` | string | no | `"2S1P"` | Pack configuration (e.g., `"2S2P"`) |

### `loads` (list)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | yes | -- | Subsystem name |
| `power_w` | float | yes | -- | Power consumption in watts |
| `duty_cycle` | float | no | `1.0` | Fraction of time active (0-1) |
| `trigger` | string | no | `"always"` | `"always"`, `"sunlight"`, or `"eclipse"` |

### `simulation`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `duration_orbits` | float | no | `10.0` | Simulation duration in orbits |
| `initial_soc` | float | no | `1.0` | Starting battery state of charge (0-1) |
| `dt_max` | float | no | `30.0` | Maximum ODE timestep in seconds |

### `simulation.thermal`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `enabled` | bool | no | `false` | Enable thermal model |
| `panel_thermal_mass_j_per_k` | float | no | `450.0` | Panel thermal mass (J/K) |
| `battery_thermal_mass_j_per_k` | float | no | `95.0` | Battery thermal mass (J/K) |
| `spacecraft_interior_temp_k` | float | no | `293.15` | Spacecraft interior temperature (K) |

## Using the builder API

```python
from satpower.mission import load_mission, build_simulation

# Load from file
config = load_mission("my_mission.yaml")

# Build and run
sim = build_simulation(config)
results = sim.run(
    duration_orbits=config.simulation.duration_orbits,
    dt_max=config.simulation.dt_max,
)
```

## Bundled mission presets

satpower ships with 5 ready-to-use mission presets in `src/satpower/data/missions/`:

| Preset | Application | Orbit | Panels | Key loads |
|--------|-------------|-------|--------|-----------|
| `earth_observation_3u` | Remote sensing | 550km SSO | Body + 2 wings, no nadir | Camera 6W @30%, ADCS, UHF |
| `iot_comms_3u` | IoT/M2M relay | 550km 45 deg | Body only | UHF @50%, beacon, GPS |
| `tech_demo_iss` | University demo | 408km 51.6 deg | Body only | Payload 3W @25%, UHF |
| `ais_maritime_3u` | Ship tracking | 600km SSO | Body + 2 wings | AIS receiver, S-band @10% |
| `scientific_6u` | Space science | 650km SSO | Body + 4 wings | Instrument 8W @40%, star tracker, reaction wheels |

### Using presets

```bash
# List available presets
satpower list missions

# Run a preset (searches bundled missions automatically)
satpower run earth_observation_3u.yaml
```

```python
from satpower.mission import load_mission, build_simulation
from pathlib import Path

# Load bundled preset by path
missions_dir = Path("src/satpower/data/missions")
config = load_mission(missions_dir / "earth_observation_3u.yaml")
sim = build_simulation(config)
results = sim.run(duration_orbits=10, dt_max=60)
```
