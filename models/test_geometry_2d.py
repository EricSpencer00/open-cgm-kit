"""Verifies the 2D/3D solvers against analytic results, then checks the A0 findings are self-consistent."""
import math
import unittest
from dataclasses import replace

import numpy as np

import electrode_model as em
import geometry_2d as g


class Analytic(unittest.TestCase):
    def test_saito_microdisk_limiting_current(self):
        # Bare disk in semi-infinite medium: i = 4 n F D C a (Saito 1968).
        a, d, c, big = 0.6e-3, 6.7e-10, 1.0, 200
        x = g.join(a * np.sin(np.pi / 2 * np.linspace(0, 1, 51)), g.one_sided_edges(a, big * a, 200))
        z = g.one_sided_edges(0, big * a, 230)
        perm = np.full((len(z) - 1, len(x) - 1), d)
        _, (flow,) = g.solve_steady(x, z, perm, np.zeros_like(perm), True,
                                    [((x[1:] <= a * (1 + 1e-9)).astype(float), 0.0)], c, outer_u=c)
        self.assertAlmostEqual(flow / (4 * d * c * a), 1.0, delta=0.01)

    def test_planar_slab_reduces_to_1d_model(self):
        # Full-width electrode, no-flux sides: the 2D solver must reproduce the 1D peroxide current.
        sensor, cond = em.PRESETS["gox_pu"], replace(em.BEAKER, glucose_mM=5.0)
        x = np.linspace(0, 1e-3, 5)
        z, perm, src, m, y1 = g.coated_problem(sensor, cond, x, False, 1e9, "peroxide")
        _, (flow,) = g.solve_steady(x, z, perm, src, False, [(np.ones(4), 0.0)], 0.0)
        want = m.grid.g_face[em.P, 0] * y1.reshape(len(em.SPECIES), m.n)[em.P, 0]
        self.assertAlmostEqual(flow / x[-1] / want, 1.0, places=6)

    def test_3d_disk_resistance(self):
        # Disk on an insulating plane: R = 1/(4 kappa a); far boundary at 40 radii costs ~1.5 %.
        a, k, big = 0.6e-3, 1.5, 40
        e = g.join(g.cosine_edges(0, a, 8), g.one_sided_edges(a, big * a, 30))
        z = g.one_sided_edges(0, big * a, 38)
        _, (i,) = g.laplace_3d(e, e, z, k, [(g.disk_weights(e, e, 0, 0, a), 1.0)], outer=("x+", "y+", "z+"))
        self.assertAlmostEqual(1 / (4 * i) * 4 * k * a, 1.0, delta=0.02)

    def test_3d_parallel_plates_exact(self):
        e = np.linspace(0, 2e-3, 5)
        z = np.linspace(0, 3e-3, 7)
        _, (i,) = g.laplace_3d(e, e, z, 2.0, [(np.ones((4, 4)), 1.0)], outer=("z+",))
        self.assertAlmostEqual(i, 2.0 * (2e-3) ** 2 / 3e-3, places=12)


class A0Layout(unittest.TestCase):
    def test_edge_error_grid_converged(self):
        cond = replace(em.BEAKER, glucose_mM=5.0)
        a = g.edge_error("gox_pu", cond, coat_radius_mm=1.1, cells_r=60, cells_per=40)
        b = g.edge_error("gox_pu", cond, coat_radius_mm=1.1, cells_r=120, cells_per=80)
        self.assertAlmostEqual(a["glucose_error_pct"], b["glucose_error_pct"], delta=1.0)

    def test_edge_effect_is_geometric_for_wide_coating(self):
        # With the coating covering the coupon, glucose and acetaminophen see the same 1D error:
        # it is the rim, not the chemistry.
        e = g.edge_error("gox_pu", replace(em.BEAKER, glucose_mM=5.0))
        self.assertAlmostEqual(e["glucose_error_pct"], e["apap_error_pct"], delta=0.5)
        self.assertLess(e["glucose_error_pct"], 0)  # 1D underestimates

    def test_peroxide_never_reaches_ce_or_re_when_stirred(self):
        x = g.crosstalk_planar(em.PRESETS["gox_pu"], replace(em.BEAKER, glucose_mM=25.0))
        self.assertLess(x["with_CE_sink"]["CE_captured_frac"], 1e-6)
        self.assertLess(x["with_CE_sink"]["c_RE_surface_uM"], 1e-3)

    def test_ir_drop_negligible_at_expected_current(self):
        ir = g.ir_drop(cell_m=3e-4)
        self.assertAlmostEqual(ir["R_uncompensated_we_re_ohm"] / ir["R_disk_to_infinity_ohm"], 1.0, delta=0.3)
        self.assertLess(ir["R_uncompensated_we_re_ohm"] * 1e-6, 1e-3)  # 1 uA drops < 1 mV


if __name__ == "__main__":
    unittest.main()
