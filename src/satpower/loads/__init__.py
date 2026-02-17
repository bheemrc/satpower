"""Power consumption — mission mode definitions and duty cycling."""

from satpower.loads._profile import LoadProfile, LoadMode
from satpower.loads._scheduler import ModeScheduler
from satpower.loads._templates import SUBSYSTEM_POWER

__all__ = [
    "LoadProfile",
    "LoadMode",
    "ModeScheduler",
    "SUBSYSTEM_POWER",
]
