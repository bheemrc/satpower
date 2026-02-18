"""satpower — CubeSat Electrical Power System Simulation Library."""

from satpower._version import __version__
from satpower.orbit._propagator import Orbit, OrbitState
from satpower.orbit._eclipse import EclipseModel, EclipseEvent
from satpower.orbit._environment import OrbitalEnvironment
from satpower.orbit._geometry import sun_vector, panel_incidence_angle
from satpower.solar._cell import SolarCell
from satpower.solar._panel import SolarPanel
from satpower.solar._mppt import MpptModel
from satpower.solar._degradation import apply_radiation_degradation
from satpower.battery._cell import BatteryCell
from satpower.battery._pack import BatteryPack
from satpower.battery._aging import AgingModel
from satpower.battery._soc import CoulombCounter
from satpower.loads._profile import LoadProfile, LoadMode
from satpower.loads._scheduler import ModeScheduler
from satpower.regulation._bus import PowerBus
from satpower.regulation._converter import DcDcConverter
from satpower.regulation._eps_board import EPSBoard
from satpower.simulation._engine import Simulation
from satpower.simulation._results import SimulationResults
from satpower.simulation._events import EclipseEventDetector
from satpower.thermal._model import ThermalModel, ThermalConfig

__all__ = [
    "__version__",
    "Orbit",
    "OrbitState",
    "EclipseModel",
    "EclipseEvent",
    "OrbitalEnvironment",
    "sun_vector",
    "panel_incidence_angle",
    "SolarCell",
    "SolarPanel",
    "MpptModel",
    "apply_radiation_degradation",
    "BatteryCell",
    "BatteryPack",
    "AgingModel",
    "CoulombCounter",
    "LoadProfile",
    "LoadMode",
    "ModeScheduler",
    "PowerBus",
    "DcDcConverter",
    "EPSBoard",
    "Simulation",
    "SimulationResults",
    "EclipseEventDetector",
    "ThermalModel",
    "ThermalConfig",
]
