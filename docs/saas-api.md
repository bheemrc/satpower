# SaaS API

satpower includes a Pydantic-based API layer for JSON-serializable request/response models. This allows integration with web frameworks like FastAPI without satpower itself depending on any web framework.

## Overview

The API layer provides:
- **Request models** -- Pydantic schemas for simulation inputs
- **Response models** -- Structured results with summary, power budget, plots
- **Service functions** -- Orchestration layer connecting schemas to satpower internals
- **Error hierarchy** -- Domain-specific exceptions with error codes

No new dependencies required -- uses only Pydantic (already a dependency) and the standard library.

## Quick start

```python
from satpower.api import (
    SimulationRequest,
    OrbitRequest,
    SolarRequest,
    BatteryRequest,
    LoadRequest,
    run_simulation,
)

request = SimulationRequest(
    name="My Mission",
    orbit=OrbitRequest(altitude_km=550, inclination_deg=97.6),
    solar=SolarRequest(cell="azur_3g30c", form_factor="3U"),
    battery=BatteryRequest(cell="panasonic_ncr18650b", config="2S2P"),
    loads=[
        LoadRequest(name="obc", power_w=0.5),
        LoadRequest(name="comms", power_w=4.0, duty_cycle=0.15),
    ],
)

response = run_simulation(request)
print(response.summary.min_soc)
print(response.power_budget.verdict)
```

## FastAPI integration

satpower is designed as a library -- your FastAPI application imports it:

```python
from fastapi import FastAPI, HTTPException
from satpower.api import (
    SimulationRequest,
    run_simulation_async,
    list_components,
    get_component,
    get_presets,
    run_preset,
    PresetSimulationRequest,
    SatpowerAPIError,
)

app = FastAPI()

@app.post("/api/v1/simulations")
async def create_simulation(request: SimulationRequest):
    try:
        return await run_simulation_async(request)
    except SatpowerAPIError as e:
        raise HTTPException(status_code=400, detail={"message": e.message, "code": e.code})

@app.get("/api/v1/components/{category}")
async def get_components_list(category: str):
    return list_components(category)

@app.get("/api/v1/components/{category}/{name}")
async def get_component_detail(category: str, name: str):
    return get_component(category, name)

@app.get("/api/v1/presets")
async def list_presets():
    return get_presets()

@app.post("/api/v1/presets/run")
async def run_preset_mission(request: PresetSimulationRequest):
    try:
        return await run_simulation_async(run_preset(request))
    except SatpowerAPIError as e:
        raise HTTPException(status_code=400, detail={"message": e.message, "code": e.code})
```

## Request schemas

### `SimulationRequest`

The main simulation request. All nested objects are Pydantic models.

```python
class SimulationRequest(BaseModel):
    name: str = "API Simulation"
    orbit: OrbitRequest
    solar: SolarRequest
    battery: BatteryRequest
    loads: list[LoadRequest] = []
    simulation: SimulationParametersRequest = SimulationParametersRequest()
    eps_board: str | None = None
    plot_format: PlotFormat = PlotFormat.STRUCTURED
    validate_system: bool = False
```

### `OrbitRequest`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `altitude_km` | float | required | Orbital altitude (km) |
| `inclination_deg` | float | required | Inclination (degrees) |
| `raan_deg` | float | 0.0 | Right Ascension of Ascending Node |
| `j2` | bool | False | Enable J2 perturbation |
| `eclipse_model` | str | "cylindrical" | "cylindrical" or "conical" |

### `SolarRequest`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `cell` | str | required | Solar cell name from database |
| `form_factor` | str | "3U" | CubeSat size: "1U", "3U", "6U" |
| `body_panels` | bool | True | Mount cells on body faces |
| `exclude_faces` | list[str] | None | Faces to skip |
| `deployed_wings_count` | int | None | Number of deployed wings (2 or 4) |
| `deployed_wings_area_m2` | float | None | Area per wing (m^2) |

### `BatteryRequest`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `cell` | str | required | Battery cell name from database |
| `config` | str | "2S1P" | Pack configuration (e.g., "2S2P") |

### `LoadRequest`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | required | Subsystem name |
| `power_w` | float | required | Power consumption (W) |
| `duty_cycle` | float | 1.0 | Fraction of time active (0-1) |
| `trigger` | str | "always" | "always", "sunlight", or "eclipse" |

### `SimulationParametersRequest`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `duration_orbits` | float | 10.0 | Simulation duration in orbits |
| `initial_soc` | float | 1.0 | Starting battery SoC (0-1) |
| `dt_max` | float | 30.0 | Maximum ODE timestep (seconds) |

### `PresetSimulationRequest`

Run a bundled preset mission:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `preset_name` | str | required | Preset name (e.g., "earth_observation_3u") |
| `overrides` | dict | {} | Override fields on the generated SimulationRequest |
| `plot_format` | PlotFormat | STRUCTURED | Plot output format |

### `PlotFormat`

Enum controlling how plots are returned:

| Value | Description |
|-------|-------------|
| `PlotFormat.STRUCTURED` | JSON time-series data (default). Best for frontend rendering. |
| `PlotFormat.PNG_BASE64` | Server-rendered PNG as base64 string. Best for emails/reports. |

## Response schemas

### `SimulationResponse`

```python
class SimulationResponse(BaseModel):
    simulation_id: str          # UUID
    name: str
    summary: SimulationSummary
    power_budget: PowerBudgetResponse
    validation: ValidationResponse | None
    plots: list[PlotData]
```

### `SimulationSummary`

| Field | Type | Description |
|-------|------|-------------|
| `min_soc` | float | Minimum state of charge |
| `max_soc` | float | Maximum state of charge |
| `worst_case_dod` | float | Maximum depth of discharge |
| `avg_power_generated_w` | float | Average generated power |
| `avg_power_consumed_w` | float | Average consumed power |
| `power_margin_w` | float | Power margin (generated - consumed) |
| `energy_balance_per_orbit_wh` | float | Net energy per orbit |
| `eclipse_fraction` | float | Fraction of time in eclipse |
| `min_battery_voltage_v` | float | Minimum battery voltage |
| `max_battery_voltage_v` | float | Maximum battery voltage |
| `duration_orbits` | float | Simulation duration |

### `PowerBudgetResponse`

| Field | Type | Description |
|-------|------|-------------|
| `mission_name` | str | Mission name |
| `subsystems` | list[dict] | Per-subsystem power breakdown |
| `avg_generated_w` | float | Average generated power |
| `avg_consumed_w` | float | Average consumed power |
| `power_margin_w` | float | Power margin |
| `eclipse_fraction` | float | Eclipse fraction |
| `worst_dod` | float | Worst depth of discharge |
| `min_soc` | float | Minimum SoC |
| `battery_energy_wh` | float | Battery pack energy |
| `verdict` | str | "POSITIVE MARGIN" or "NEGATIVE MARGIN" |

### `PlotData`

Each simulation returns 3 plots (SoC, power balance, battery voltage):

```python
class PlotData(BaseModel):
    plot_type: str                           # "soc", "power_balance", "battery_voltage"
    format: PlotFormat
    time_series: list[TimeSeriesData] | None # when STRUCTURED
    png_base64: str | None                   # when PNG_BASE64
    eclipse_regions: list[tuple[float, float]]  # (start, end) in orbit units
```

### `TimeSeriesData`

```python
class TimeSeriesData(BaseModel):
    label: str       # e.g., "SoC", "Power Generated"
    unit: str        # e.g., "%", "W", "V"
    x: list[float]   # time values (orbits)
    y: list[float]   # data values
```

### `ValidationResponse`

Returned when `validate_system=True` and `eps_board` is provided:

| Field | Type | Description |
|-------|------|-------------|
| `passed` | bool | All checks passed |
| `warnings` | list[str] | Non-critical issues |
| `errors` | list[str] | Critical incompatibilities |

## Service functions

### `run_simulation(request) -> SimulationResponse`

Synchronous simulation execution. Validates component names, builds domain objects, runs the ODE simulation, and serializes the response.

### `run_simulation_async(request) -> SimulationResponse`

Async wrapper for `run_simulation`. Runs the CPU-bound simulation in a `ThreadPoolExecutor` (4 workers) so it doesn't block the event loop.

### `run_preset(request) -> SimulationResponse`

Loads a bundled preset by name, converts it to a `SimulationRequest`, applies overrides, and delegates to `run_simulation`.

### `list_components(category) -> ComponentListResponse`

Lists all components in a category. Valid categories: `"solar_cells"`, `"battery_cells"`, `"eps"`.

### `get_component(category, name) -> ComponentDetailResponse`

Returns full datasheet for a single component.

### `get_presets() -> PresetListResponse`

Lists all bundled mission presets with their application type.

## Error handling

All API errors inherit from `SatpowerAPIError`:

| Exception | Code | When raised |
|-----------|------|-------------|
| `SatpowerAPIError` | `UNKNOWN_ERROR` | Base class |
| `ComponentNotFoundError` | `COMPONENT_NOT_FOUND` | Invalid solar cell, battery, or EPS name |
| `InvalidConfigurationError` | `INVALID_CONFIGURATION` | Invalid category or parameter |
| `SimulationError` | `SIMULATION_FAILED` | ODE solver or physics error |
| `PresetNotFoundError` | `PRESET_NOT_FOUND` | Unknown preset name |

Each exception has `message`, `code`, and `details` attributes:

```python
from satpower.api import run_simulation, ComponentNotFoundError

try:
    response = run_simulation(request)
except ComponentNotFoundError as e:
    print(e.code)      # "COMPONENT_NOT_FOUND"
    print(e.message)   # "solar_cell component not found: 'bad_name'"
    print(e.details)   # {"category": "solar_cell", "name": "bad_name"}
```

## JSON example

### Request

```json
{
  "name": "Earth Observer",
  "orbit": {
    "altitude_km": 550,
    "inclination_deg": 97.6,
    "j2": true,
    "eclipse_model": "conical"
  },
  "solar": {
    "cell": "azur_3g30c",
    "form_factor": "3U",
    "exclude_faces": ["-Z"],
    "deployed_wings_count": 2,
    "deployed_wings_area_m2": 0.06
  },
  "battery": {
    "cell": "panasonic_ncr18650b",
    "config": "2S2P"
  },
  "loads": [
    {"name": "obc", "power_w": 0.5},
    {"name": "camera", "power_w": 6.0, "duty_cycle": 0.3, "trigger": "sunlight"},
    {"name": "comms", "power_w": 4.0, "duty_cycle": 0.15}
  ],
  "simulation": {
    "duration_orbits": 5,
    "initial_soc": 1.0,
    "dt_max": 30.0
  },
  "plot_format": "structured"
}
```

### Response (abbreviated)

```json
{
  "simulation_id": "a1b2c3d4-...",
  "name": "Earth Observer",
  "summary": {
    "min_soc": 0.972,
    "max_soc": 1.0,
    "worst_case_dod": 0.028,
    "avg_power_generated_w": 4.15,
    "avg_power_consumed_w": 2.60,
    "power_margin_w": 1.55,
    "eclipse_fraction": 0.375,
    "duration_orbits": 5.0
  },
  "power_budget": {
    "mission_name": "Earth Observer",
    "verdict": "POSITIVE MARGIN"
  },
  "plots": [
    {
      "plot_type": "soc",
      "format": "structured",
      "time_series": [
        {"label": "SoC", "unit": "%", "x": [0.0, 0.01, ...], "y": [100.0, 99.98, ...]}
      ],
      "eclipse_regions": [[0.31, 0.69], [1.31, 1.69]]
    }
  ]
}
```
