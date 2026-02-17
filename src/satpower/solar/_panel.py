"""Solar panel geometry — body-mounted and deployed panels."""

from __future__ import annotations

import numpy as np

from satpower.solar._cell import SolarCell

# CubeSat face dimensions (meters)
_CUBESAT_FACE = {
    "1U": {"long": (0.10, 0.10), "short": (0.10, 0.10)},
    "3U": {"long": (0.30, 0.10), "short": (0.10, 0.10)},
    "6U": {"long": (0.30, 0.20), "short": (0.10, 0.20)},
}

# Face normals in body frame: +X, -X, +Y, -Y, +Z, -Z
_FACE_NORMALS = {
    "+X": np.array([1.0, 0.0, 0.0]),
    "-X": np.array([-1.0, 0.0, 0.0]),
    "+Y": np.array([0.0, 1.0, 0.0]),
    "-Y": np.array([0.0, -1.0, 0.0]),
    "+Z": np.array([0.0, 0.0, 1.0]),
    "-Z": np.array([0.0, 0.0, -1.0]),
}


class SolarPanel:
    """A panel of solar cells with defined geometry and orientation."""

    def __init__(
        self,
        area_m2: float,
        cell: SolarCell,
        normal: np.ndarray,
        name: str = "",
    ):
        self._area_m2 = area_m2
        self._cell = cell
        self._normal = np.asarray(normal, dtype=float)
        self._normal = self._normal / np.linalg.norm(self._normal)
        self._name = name

    @classmethod
    def cubesat_body(cls, form_factor: str, cell_type: str) -> list[SolarPanel]:
        """Create body-mounted panels for a CubeSat.

        Returns one panel per face (6 panels). For 3U and 6U, the ±X and ±Z
        faces are "long" faces, ±Y are "short" faces.

        Parameters
        ----------
        form_factor : "1U", "3U", or "6U"
        cell_type : solar cell name (e.g. "azur_3g30c")
        """
        if form_factor not in _CUBESAT_FACE:
            raise ValueError(f"Unknown CubeSat form factor: {form_factor!r}")

        cell = SolarCell.from_datasheet(cell_type)
        dims = _CUBESAT_FACE[form_factor]

        panels = []
        for face_name, normal in _FACE_NORMALS.items():
            # ±Y faces are always "short" dimension, others are "long"
            if "Y" in face_name:
                w, h = dims["short"]
            else:
                w, h = dims["long"]

            area = w * h * cell.packing_factor
            panels.append(
                cls(
                    area_m2=area,
                    cell=cell,
                    normal=normal,
                    name=f"{form_factor}_{face_name}",
                )
            )

        return panels

    @classmethod
    def deployed(
        cls,
        area_m2: float,
        cell_type: str,
        normal: np.ndarray,
        name: str = "deployed",
    ) -> SolarPanel:
        """Create a deployed (non body-mounted) solar panel."""
        cell = SolarCell.from_datasheet(cell_type)
        return cls(area_m2=area_m2, cell=cell, normal=normal, name=name)

    @property
    def area_m2(self) -> float:
        return self._area_m2

    @property
    def normal(self) -> np.ndarray:
        return self._normal.copy()

    @property
    def name(self) -> str:
        return self._name

    @property
    def cell(self) -> SolarCell:
        return self._cell

    def power(
        self,
        sun_direction: np.ndarray,
        irradiance: float,
        temperature_k: float,
        mppt_efficiency: float = 0.97,
    ) -> float:
        """Compute panel power output (W).

        Parameters
        ----------
        sun_direction : (3,) unit vector toward Sun in body frame
        irradiance : solar irradiance at satellite (W/m^2)
        temperature_k : panel temperature (K)
        mppt_efficiency : MPPT tracking efficiency (default 0.97)
        """
        # Cosine of incidence angle
        cos_angle = float(np.dot(sun_direction, self._normal))
        if cos_angle <= 0:
            return 0.0  # Panel faces away from Sun

        # Effective irradiance on panel
        effective_irradiance = irradiance * cos_angle

        # Power output of a single cell at this irradiance
        power_per_cell = self._cell.power_at_mpp(
            effective_irradiance, temperature_k
        )

        # Scale by number of cells that fit on this panel
        n_cells = self._area_m2 / self._cell.area_m2
        total_power = power_per_cell * n_cells * mppt_efficiency

        return max(0.0, total_power)
