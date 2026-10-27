"""Checks the numerical model against closed-form limits and conservation laws."""
import math
import unittest
from dataclasses import replace

import numpy as np

import electrode_model as em


def series_resistance(model: em.Model, species: int) -> float:
    """Sum of L/D over every layer including the boundary layer, s/m."""
    wd = em.water_d(model.cond.temp_c)
    name = em.SPECIES[species]
    layers = list(model.sensor.layers) + [
        em.Layer("boundary", model.cond.boundary_um, {s: model.cond.boundary_d_ratio for s in em.SPECIES})
    ]
    return sum(l.thickness_um * 1e-6 / (wd[name] * l.d_ratio[name] * l.k(name)) for l in layers)


class TransportLimits(unittest.TestCase):
    def test_peroxide_only_matches_series_diffusion(self):
        sensor = replace(em.PRESETS["gox_pu"], enzyme_u_per_cm2=0.0)
        cond = replace(em.BEAKER, glucose_mM=0.0, peroxide_mM=0.1)
        m = em.Model(sensor, cond)
        got = m.current_nA(m.steady())["peroxide"]
        want = 2 * em.F * 0.1 / series_resistance(m, em.P) * sensor.area_mm2 * 1e-6 * 1e9
        self.assertAlmostEqual(got / want, 1.0, places=3)

    def test_acetaminophen_oxidized_only_on_pt(self):
        cond = replace(em.BEAKER, glucose_mM=0.0, acetaminophen_mM=0.13)
        pt = em.Model(em.PRESETS["gox_pu"], cond)
        got = pt.current_nA(pt.steady())["acetaminophen"]
        want = 2 * em.F * 0.13 / series_resistance(pt, em.A) * pt.sensor.area_mm2 * 1e-6 * 1e9
        self.assertAlmostEqual(got / want, 1.0, places=3)
        pb = em.Model(em.PRESETS["pb_gox_pu"], cond)
        self.assertEqual(pb.current_nA(pb.steady())["acetaminophen"], 0.0)

    def test_enzyme_excess_is_glucose_flux_limited(self):
        # Huge enzyme activity and oxygen: glucose reacts at the enzyme/membrane
        # boundary; peroxide splits between electrode and bulk by resistance.
        sensor = replace(em.PRESETS["gox_pu"], enzyme_u_per_cm2=1e4, km_oxygen_mM=1e-4)
        cond = replace(em.BEAKER, glucose_mM=2.0, oxygen_mM=50.0)
        m = em.Model(sensor, cond)
        got = m.current_nA(m.steady())["peroxide"]
        wd = em.water_d(cond.temp_c)
        enz, mem = sensor.layers
        r = lambda layer, s: layer.thickness_um * 1e-6 / (wd[s] * layer.d_ratio[s] * layer.k(s))
        bl = cond.boundary_um * 1e-6
        r_glucose_out = r(mem, "glucose") + bl / wd["glucose"]
        r_p_in, r_p_out = r(enz, "peroxide"), r(mem, "peroxide") + bl / wd["peroxide"]
        collection = r_p_out / (r_p_in + r_p_out)
        want = 2 * em.F * 2.0 / r_glucose_out * collection * sensor.area_mm2 * 1e-6 * 1e9
        self.assertAlmostEqual(got / want, 1.0, delta=0.03)


class Conservation(unittest.TestCase):
    def test_glucose_consumed_equals_peroxide_out(self):
        m = em.Model(em.PRESETS["gox_pu"], replace(em.BEAKER, glucose_mM=8.0))
        c = m.steady().reshape(len(em.SPECIES), m.n)
        g = m.grid.g_face
        glucose_in = g[em.G, -1] * (8.0 - c[em.G, -1])
        to_electrode = g[em.P, 0] * c[em.P, 0]
        to_bulk = g[em.P, -1] * c[em.P, -1]
        self.assertAlmostEqual((to_electrode + to_bulk) / glucose_in, 1.0, places=4)
        self.assertAlmostEqual(float((m.rate(c) * m.grid.h).sum()) / glucose_in, 1.0, places=4)

    def test_partition_sets_storage_not_steady_flux(self):
        # Same permeability D*K, ten times lower D: identical steady current, slower step.
        base = em.PRESETS["gox_pu"]
        enz, mem = base.layers
        slow = replace(mem, d_ratio={s: v / 10 for s, v in mem.d_ratio.items()},
                       partition={s: mem.k(s) * 10 for s in em.SPECIES})
        results = []
        for sensor in (base, replace(base, layers=(enz, slow))):
            m = em.Model(sensor, replace(em.BEAKER, glucose_mM=5.0))
            y = m.steady()
            t, i = m.step(y, replace(em.BEAKER, glucose_mM=10.0).bulk(), t_end=3600, points=1200)
            results.append((m.total_nA(y), em.t90_s(t, i)))
        self.assertAlmostEqual(results[0][0] / results[1][0], 1.0, places=4)
        self.assertGreater(results[1][1], 2 * results[0][1])

    def test_grid_converged(self):
        def current(cells):
            s = em.PRESETS["gox_pu"]
            layers = tuple(replace(l, cells=cells) for l in s.layers)
            m = em.Model(replace(s, layers=layers), replace(em.TISSUE, glucose_mM=10.0))
            return m.total_nA(m.steady())
        self.assertLess(abs(current(20) / current(60) - 1), 0.01)


class Behaviour(unittest.TestCase):
    def test_calibration_monotonic_and_oxygen_limited(self):
        conc = np.array([0, 2, 5, 10, 20, 30.0])
        beaker = em.calibration(em.PRESETS["gox_pu"], em.BEAKER, conc)
        self.assertTrue(np.all(np.diff(beaker) > 0))
        low_o2 = em.calibration(em.PRESETS["gox_pu"], replace(em.BEAKER, oxygen_mM=0.02), conc)
        self.assertLess(low_o2[-1], beaker[-1])

    def test_readout_lsb_matches_firmware_formula(self):
        row = next(r for r in em.readout(100, 1) if r["rtia"] == "10K")
        self.assertAlmostEqual(row["lsb_nA"], 1.82 / 1.5 / 32768 / 10e3 * 1e9)
        self.assertTrue(math.isclose(row["lsb_nA"], 3.703, rel_tol=1e-3))


if __name__ == "__main__":
    unittest.main()
