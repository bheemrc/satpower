"""Event detection for simulation — eclipse transitions, DoD floor."""

from __future__ import annotations

import numpy as np


class EclipseEventDetector:
    """Detects eclipse entry/exit from shadow fraction array."""

    @staticmethod
    def find_transitions(
        times: np.ndarray, eclipse: np.ndarray
    ) -> list[dict]:
        """Find eclipse entry/exit events from boolean eclipse array.

        Returns list of dicts with 'time' and 'type' ('entry' or 'exit').
        """
        events = []
        for i in range(1, len(eclipse)):
            if not eclipse[i - 1] and eclipse[i]:
                t_event = 0.5 * (times[i - 1] + times[i])
                events.append({"time": t_event, "type": "entry"})
            elif eclipse[i - 1] and not eclipse[i]:
                t_event = 0.5 * (times[i - 1] + times[i])
                events.append({"time": t_event, "type": "exit"})
        return events

    @staticmethod
    def eclipse_fraction(eclipse: np.ndarray) -> float:
        """Compute fraction of time spent in eclipse."""
        return float(np.mean(eclipse.astype(float)))
