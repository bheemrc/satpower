"""satpower API layer — JSON-serializable request/response models and services."""

from satpower.api._errors import (
    SatpowerAPIError,
    ComponentNotFoundError,
    InvalidConfigurationError,
    SimulationError,
    PresetNotFoundError,
)
from satpower.api._schemas import (
    PlotFormat,
    OrbitRequest,
    SolarRequest,
    BatteryRequest,
    LoadRequest,
    SimulationParametersRequest,
    SimulationRequest,
    PresetSimulationRequest,
    TimeSeriesData,
    PlotData,
    SimulationSummary,
    PowerBudgetResponse,
    ValidationResponse,
    SimulationResponse,
    ComponentInfo,
    ComponentListResponse,
    ComponentDetailResponse,
    PresetInfo,
    PresetListResponse,
)
from satpower.api._services import (
    run_simulation,
    run_simulation_async,
    run_preset,
    list_components,
    get_component,
    get_presets,
)

__all__ = [
    # Errors
    "SatpowerAPIError",
    "ComponentNotFoundError",
    "InvalidConfigurationError",
    "SimulationError",
    "PresetNotFoundError",
    # Schemas
    "PlotFormat",
    "OrbitRequest",
    "SolarRequest",
    "BatteryRequest",
    "LoadRequest",
    "SimulationParametersRequest",
    "SimulationRequest",
    "PresetSimulationRequest",
    "TimeSeriesData",
    "PlotData",
    "SimulationSummary",
    "PowerBudgetResponse",
    "ValidationResponse",
    "SimulationResponse",
    "ComponentInfo",
    "ComponentListResponse",
    "ComponentDetailResponse",
    "PresetInfo",
    "PresetListResponse",
    # Services
    "run_simulation",
    "run_simulation_async",
    "run_preset",
    "list_components",
    "get_component",
    "get_presets",
]
