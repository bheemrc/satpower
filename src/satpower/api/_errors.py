"""Domain-specific exceptions for the satpower API."""

from __future__ import annotations


class SatpowerAPIError(Exception):
    """Base exception for satpower API errors."""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR", details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class ComponentNotFoundError(SatpowerAPIError):
    """Raised when a component is not found in the registry."""

    def __init__(self, category: str, name: str):
        super().__init__(
            message=f"{category} component not found: {name!r}",
            code="COMPONENT_NOT_FOUND",
            details={"category": category, "name": name},
        )


class InvalidConfigurationError(SatpowerAPIError):
    """Raised when a configuration is invalid."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message=message,
            code="INVALID_CONFIGURATION",
            details=details or {},
        )


class SimulationError(SatpowerAPIError):
    """Raised when a simulation fails."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message=message,
            code="SIMULATION_FAILED",
            details=details or {},
        )


class PresetNotFoundError(SatpowerAPIError):
    """Raised when a preset mission is not found."""

    def __init__(self, name: str):
        super().__init__(
            message=f"Preset mission not found: {name!r}",
            code="PRESET_NOT_FOUND",
            details={"name": name},
        )
