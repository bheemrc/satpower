"""Simulation engine — ODE integration, event detection, results, reports."""

from satpower.simulation._engine import Simulation
from satpower.simulation._results import SimulationResults
from satpower.simulation._events import EclipseEventDetector
from satpower.simulation._report import PowerBudgetReport, generate_power_budget

__all__ = [
    "Simulation",
    "SimulationResults",
    "EclipseEventDetector",
    "PowerBudgetReport",
    "generate_power_budget",
]
