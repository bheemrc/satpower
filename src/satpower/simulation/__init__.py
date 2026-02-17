"""Simulation engine — ODE integration, event detection, results."""

from satpower.simulation._engine import Simulation
from satpower.simulation._results import SimulationResults
from satpower.simulation._events import EclipseEventDetector

__all__ = [
    "Simulation",
    "SimulationResults",
    "EclipseEventDetector",
]
