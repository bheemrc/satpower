# CLI Reference

satpower provides a command-line tool for running simulations and listing components.

## Usage

```bash
satpower <command> [arguments]
```

Or via Python module:

```bash
python -m satpower <command> [arguments]
```

## Commands

### `satpower run`

Run a mission simulation from a YAML file and print the power budget report.

```bash
satpower run <mission.yaml> [--plot] [--save-plots DIR]
```

| Argument | Description |
|----------|-------------|
| `mission.yaml` | Path to mission YAML file. Also searches bundled presets. |
| `--plot` | Show interactive matplotlib plots (SoC, power, voltage) |
| `--save-plots DIR` | Save plots as PNG files to the specified directory |

**Examples:**

```bash
# Run with text report only
satpower run my_mission.yaml

# Run and show interactive plots
satpower run my_mission.yaml --plot

# Save plots to a directory
satpower run my_mission.yaml --save-plots results/

# Run a bundled preset
satpower run earth_observation_3u.yaml
```

**Saved plot files** (when using `--save-plots`):
- `soc.png` -- battery state of charge over time
- `power_balance.png` -- generated vs consumed power
- `battery_voltage.png` -- battery terminal voltage

### `satpower list`

List available components from the database.

```bash
satpower list <category>
```

| Category | Description |
|----------|-------------|
| `cells` | Solar cells with name and efficiency |
| `batteries` | Battery cells with capacity and voltage |
| `eps` | EPS boards with bus voltage |
| `missions` | Bundled mission presets |

**Examples:**

```bash
$ satpower list cells
Available solar cells:
  azur_3g30c                      Azur Space 3G30C  (eff=30.0%)
  azur_4g32c                      Azur Space 4G32C  (eff=32.0%)
  cesi_ctj30                      CESI CTJ30  (eff=30.0%)
  solaero_ztj                     SolAero ZTJ  (eff=29.5%)
  spectrolab_utj                  SpectroLab UTJ  (eff=28.3%)
  spectrolab_xtj_prime            Spectrolab XTJ Prime  (eff=30.7%)

$ satpower list batteries
Available battery cells:
  lg_mj1                          LG MJ1  (3.5Ah, 3.6V)
  panasonic_ncr18650b             Panasonic NCR18650B  (3.4Ah, 3.6V)
  saft_mp176065                   Saft MP176065  (6.5Ah, 3.6V)
  samsung_inr18650_30q            Samsung INR18650-30Q  (3.0Ah, 3.6V)
  sony_vtc6                       Sony VTC6  (3.0Ah, 3.6V)

$ satpower list eps
Available EPS boards:
  clydespace_3g_eps               Clyde Space 3rd Gen EPS  (bus=5.0V)
  endurosat_eps_i_plus            EnduroSat EPS I+  (bus=3.3V)
  gomspace_p31u                   GomSpace P31u  (bus=3.3V)
  isis_ieps                       ISIS iEPS  (bus=3.3V)

$ satpower list missions
Bundled mission presets:
  ais_maritime_3u
  earth_observation_3u
  iot_comms_3u
  scientific_6u
  tech_demo_iss
```
