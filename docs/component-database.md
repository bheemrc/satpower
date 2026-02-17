# Component Database

satpower ships with YAML datasheets for real CubeSat components. Components are auto-discovered from `src/satpower/data/`.

## Solar cells

Located in `src/satpower/data/cells/`.

| Name | Datasheet name | Type | Efficiency | Voc (V) | Isc (A) | Area (cm^2) |
|------|----------------|------|-----------|---------|---------|-------------|
| `azur_3g30c` | Azur Space 3G30C | Triple junction | 30.0% | 2.700 | 0.520 | 30.18 |
| `azur_4g32c` | Azur Space 4G32C | Quad junction | 32.0% | 3.480 | 0.425 | 30.18 |
| `cesi_ctj30` | CESI CTJ30 | Triple junction | 30.0% | 2.690 | 0.527 | 30.18 |
| `solaero_ztj` | SolAero ZTJ | Triple junction | 29.5% | 2.730 | 0.485 | 27.60 |
| `spectrolab_utj` | SpectroLab UTJ | Triple junction | 28.3% | 2.660 | 0.472 | 27.50 |
| `spectrolab_xtj_prime` | Spectrolab XTJ Prime | Triple junction | 30.7% | 2.720 | 0.478 | 26.62 |

### How to use

```python
from satpower.solar import SolarCell, SolarPanel

# Load individual cell
cell = SolarCell.from_datasheet("azur_3g30c")
print(cell.efficiency, cell.voc, cell.isc)

# Use in panels
panels = SolarPanel.cubesat_body("3U", cell_type="azur_3g30c")
```

### Cell model

Each cell uses a single-diode equivalent circuit model with:
- I-V curve generation via implicit equation solving (Brentq)
- Maximum power point tracking (fill factor approximation for speed)
- Temperature coefficients (Voc, Isc, Pmp)
- Radiation degradation factors (remaining factor at 1e14 and 1e15 fluence)

## Batteries

Located in `src/satpower/data/batteries/`.

| Name | Datasheet name | Chemistry | Capacity (Ah) | Nom. V | Form factor |
|------|----------------|-----------|---------------|--------|-------------|
| `panasonic_ncr18650b` | Panasonic NCR18650B | NCA | 3.35 | 3.6V | 18650 |
| `sony_vtc6` | Sony VTC6 | NMC | 3.0 | 3.6V | 18650 |
| `samsung_inr18650_30q` | Samsung INR18650-30Q | NMC | 3.0 | 3.6V | 18650 |
| `lg_mj1` | LG MJ1 | NMC | 3.5 | 3.6V | 18650 |
| `saft_mp176065` | Saft MP176065 | LFP | 6.5 | 3.65V | Prismatic |

### How to use

```python
from satpower.battery import BatteryCell, BatteryPack

# Individual cell
cell = BatteryCell.from_datasheet("panasonic_ncr18650b")
print(cell.capacity_ah, cell.nominal_voltage)

# Battery pack
pack = BatteryPack.from_cell("panasonic_ncr18650b", config="2S2P")
print(pack.energy_wh)  # 48.2 Wh
```

### Battery model

Each cell uses a 2nd-order Thevenin equivalent circuit:
- Open-circuit voltage (OCV) as function of SoC (interpolated from table)
- Internal resistance R0 with Arrhenius temperature dependence
- Two R-C time constants for transient response
- Calendar and cycle aging model

## EPS boards

Located in `src/satpower/data/eps/`.

| Name | Datasheet name | Bus voltage | Max solar in | Solar inputs | Battery config |
|------|----------------|-------------|-------------|-------------|---------------|
| `gomspace_p31u` | GomSpace P31u | 3.3V | 6.5V / 1.5A | 6 | 2S1P |
| `clydespace_3g_eps` | Clyde Space 3rd Gen | 5.0V | 7.0V / 2.0A | 7 | 2S1P |
| `endurosat_eps_i_plus` | EnduroSat EPS I+ | 3.3V | 6.0V / 1.2A | 6 | 2S1P |
| `isis_ieps` | ISIS iEPS | 3.3V | 6.5V / 1.5A | 6 | 2S1P |

### How to use

```python
from satpower.regulation import EPSBoard

eps = EPSBoard.from_datasheet("gomspace_p31u")
print(eps.bus_voltage)           # 3.3
print(eps.mppt_efficiency)       # 0.97
print(eps.converter_efficiency)  # 0.92

# Pass to simulation
sim = Simulation(orbit, panels, battery, loads, eps_board=eps)
```

### What the EPS board provides

When you pass an `EPSBoard` to a `Simulation`, it overrides:
- **Bus voltage** -- the regulated output voltage
- **MPPT efficiency** -- how well solar power is tracked
- **Converter efficiency** -- DC-DC conversion losses

## Adding custom components

Create a YAML file following the schema and place it in the appropriate directory:

- Solar cells: `src/satpower/data/cells/{name}.yaml`
- Batteries: `src/satpower/data/batteries/{name}.yaml`
- EPS boards: `src/satpower/data/eps/{name}.yaml`

The component registry auto-discovers all `.yaml` files in these directories.

### Solar cell YAML schema

```yaml
name: "Your Cell Name"
type: "triple_junction"
junctions: ["InGaP", "GaAs", "Ge"]
test_conditions:
  spectrum: "AM0"
  irradiance_w_m2: 1361.0
  temperature_c: 28.0
parameters:
  voc_v: 2.700
  isc_a: 0.520
  vmp_v: 2.411
  imp_a: 0.504
  efficiency: 0.300
  area_cm2: 30.18
diode_model:
  ideality_factor: 1.2
  series_resistance_ohm: 0.005
  shunt_resistance_ohm: 10000.0
temperature_coefficients:
  dvoc_dt_mv_per_c: -6.0
  disc_dt_ua_cm2_per_c: 10.0
  dpmp_dt_percent_per_c: -0.04
radiation:
  remaining_factor_1e14: 0.93
  remaining_factor_1e15: 0.88
optical:
  absorptance: 0.91
  emittance: 0.85
  packing_factor: 0.90
```

### Battery cell YAML schema

```yaml
name: "Your Battery"
chemistry: "NMC"
form_factor: "18650"
nominal_voltage_v: 3.6
capacity_ah: 3.0
max_charge_voltage_v: 4.2
min_discharge_voltage_v: 2.5
max_charge_current_a: 4.0
max_discharge_current_a: 15.0
mass_g: 46.0
thevenin_model:
  ro_ohm: 0.025
  r1_ohm: 0.012
  c1_f: 280.0
  r2_ohm: 0.004
  c2_f: 1900.0
ocv_soc_table:
  - [0.0, 3.10]
  - [0.1, 3.35]
  - [0.5, 3.75]
  - [1.0, 4.20]
temperature:
  ro_activation_energy_j: 19000.0
  reference_temp_c: 25.0
  capacity_derating:
    - [-20, 0.68]
    - [25, 1.00]
    - [45, 0.97]
aging:
  calendar_fade_per_year_25c: 0.02
  cycle_fade_per_cycle_50dod: 0.0001
  cycle_fade_per_cycle_100dod: 0.0005
```

### EPS board YAML schema

```yaml
name: "Your EPS"
bus_voltage_v: 3.3
bus_voltage_range_v: [3.0, 5.0]
max_solar_input_v: 6.5
max_solar_input_a: 1.5
converter_efficiency: 0.92
mppt_efficiency: 0.97
battery_config: "2S1P"
num_solar_inputs: 6
max_output_channels: 6
mass_g: 75.0
```

## Browsing components

### CLI

```bash
satpower list cells
satpower list batteries
satpower list eps
```

### Python

```python
from satpower.data import registry

registry.list_solar_cells()    # ['azur_3g30c', 'azur_4g32c', ...]
registry.list_battery_cells()  # ['lg_mj1', 'panasonic_ncr18650b', ...]
registry.list_eps()            # ['clydespace_3g_eps', 'gomspace_p31u', ...]
registry.list_missions()       # ['earth_observation_3u', ...]
```
