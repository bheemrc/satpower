"""NumPy-to-JSON and matplotlib-to-base64 serializers for the API."""

from __future__ import annotations

import base64
import io

import numpy as np

from satpower.api._schemas import (
    PlotData,
    PlotFormat,
    TimeSeriesData,
)
from satpower.simulation._results import SimulationResults


def _extract_eclipse_regions(results: SimulationResults) -> list[tuple[float, float]]:
    """Extract eclipse regions as (start_orbit, end_orbit) pairs."""
    t_orbits = results.time_orbits
    regions = []
    in_ecl = False
    start = 0.0

    for i in range(len(results.eclipse)):
        if results.eclipse[i] and not in_ecl:
            start = float(t_orbits[i])
            in_ecl = True
        elif not results.eclipse[i] and in_ecl:
            regions.append((start, float(t_orbits[i])))
            in_ecl = False
    if in_ecl:
        regions.append((start, float(t_orbits[-1])))

    return regions


def _fig_to_base64(fig) -> str:
    """Render matplotlib figure to base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("ascii")
    buf.close()
    # Use the same safe pyplot import as _results.py
    from satpower.simulation._results import _pyplot
    plt = _pyplot()
    plt.close(fig)
    return encoded


def serialize_plot_soc(
    results: SimulationResults, fmt: PlotFormat
) -> PlotData:
    """Serialize SoC plot as structured data or base64 PNG."""
    eclipse_regions = _extract_eclipse_regions(results)

    if fmt == PlotFormat.STRUCTURED:
        return PlotData(
            plot_type="soc",
            format=fmt,
            time_series=[
                TimeSeriesData(
                    label="State of Charge",
                    unit="%",
                    x=results.time_orbits.tolist(),
                    y=(results.soc * 100).tolist(),
                )
            ],
            eclipse_regions=eclipse_regions,
        )

    # PNG_BASE64
    fig = results.plot_soc()
    return PlotData(
        plot_type="soc",
        format=fmt,
        png_base64=_fig_to_base64(fig),
        eclipse_regions=eclipse_regions,
    )


def serialize_plot_power_balance(
    results: SimulationResults, fmt: PlotFormat
) -> PlotData:
    """Serialize power balance plot."""
    eclipse_regions = _extract_eclipse_regions(results)

    if fmt == PlotFormat.STRUCTURED:
        return PlotData(
            plot_type="power_balance",
            format=fmt,
            time_series=[
                TimeSeriesData(
                    label="Generated",
                    unit="W",
                    x=results.time_orbits.tolist(),
                    y=results.power_generated.tolist(),
                ),
                TimeSeriesData(
                    label="Consumed",
                    unit="W",
                    x=results.time_orbits.tolist(),
                    y=results.power_consumed.tolist(),
                ),
            ],
            eclipse_regions=eclipse_regions,
        )

    fig = results.plot_power_balance()
    return PlotData(
        plot_type="power_balance",
        format=fmt,
        png_base64=_fig_to_base64(fig),
        eclipse_regions=eclipse_regions,
    )


def serialize_plot_battery_voltage(
    results: SimulationResults, fmt: PlotFormat
) -> PlotData:
    """Serialize battery voltage plot."""
    eclipse_regions = _extract_eclipse_regions(results)

    if fmt == PlotFormat.STRUCTURED:
        return PlotData(
            plot_type="battery_voltage",
            format=fmt,
            time_series=[
                TimeSeriesData(
                    label="Battery Voltage",
                    unit="V",
                    x=results.time_orbits.tolist(),
                    y=results.battery_voltage.tolist(),
                )
            ],
            eclipse_regions=eclipse_regions,
        )

    fig = results.plot_battery_voltage()
    return PlotData(
        plot_type="battery_voltage",
        format=fmt,
        png_base64=_fig_to_base64(fig),
        eclipse_regions=eclipse_regions,
    )
