#!/usr/bin/env python3
"""ISS-altitude orbit power analysis — 408 km, 51.6° inclination."""

import satpower as sp


def main():
    # ISS-like orbit
    orbit = sp.Orbit.circular(altitude_km=408, inclination_deg=51.6)
    print(f"Orbit: {orbit.altitude_km:.0f} km, {orbit.inclination_deg:.1f}° inc")
    print(f"Period: {orbit.period / 60:.1f} min")

    # 3U with Spectrolab cells
    panels = sp.SolarPanel.cubesat_body("3U", cell_type="spectrolab_xtj_prime")

    # 2S1P battery
    battery = sp.BatteryPack.from_cell("panasonic_ncr18650b", config="2S1P")
    print(f"Battery: {battery.energy_wh:.1f} Wh")

    # Conservative loads
    loads = sp.LoadProfile()
    loads.add_mode("idle", power_w=1.5)
    loads.add_mode("adcs", power_w=1.0, duty_cycle=0.8)
    loads.add_mode("comms", power_w=6.0, duty_cycle=0.10, trigger="sunlight")

    # Run 10 orbits
    sim = sp.Simulation(orbit, panels, battery, loads)
    results = sim.run(duration_orbits=10, dt_max=60)

    print("\n--- Results ---")
    for k, v in results.summary().items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
