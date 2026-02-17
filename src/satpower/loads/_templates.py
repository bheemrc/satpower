"""Standard subsystem power draws for CubeSat missions."""

from __future__ import annotations

SUBSYSTEM_POWER: dict[str, float] = {
    "obc_arm": 0.4,
    "obc_msp430": 0.15,
    "adcs_magnetorquer": 0.8,
    "adcs_reaction_wheel": 2.5,
    "uhf_transceiver": 4.0,
    "sband_transmitter": 8.0,
    "xband_transmitter": 12.0,
    "camera_vis": 5.0,
    "camera_multispectral": 8.0,
    "gps_receiver": 0.8,
    "star_tracker": 1.5,
    "heater_battery": 1.0,
    "beacon": 0.3,
    "ais_receiver": 1.0,
}
