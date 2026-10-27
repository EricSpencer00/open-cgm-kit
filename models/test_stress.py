"""Failure-mode trace generator: each mode must move the trace the way its mechanism says."""
import re
import unittest
from pathlib import Path

import numpy as np

import electrode_model as em
import stress_fixtures

RESULT = em.characterize("gox_pu_tissue", em.PRESETS["gox_pu_tissue"])
HOURS = 48.0


def trace(failures):
    return em.synthetic_trace(RESULT, HOURS, 300.0, "512K", seed=7, failures=failures)


class Failures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nominal = trace(None)
        cls.same_noise = trace(em.Failures())  # all modes off must match the legacy generator closely

    def window(self, tr, h0, h1):
        t = tr[:, 0] / 3600
        return tr[(t >= h0) & (t < h1), 3].mean()

    def test_default_path_unchanged_for_24h(self):
        a = em.synthetic_trace(RESULT, 24.0, 60.0)
        b = em.synthetic_trace(RESULT, 24.0, 60.0, failures=None)
        np.testing.assert_array_equal(a, b)
        self.assertEqual(a.shape, (1440, 4))

    def test_all_off_matches_nominal(self):
        rel = np.abs(self.same_noise[:, 3] - self.nominal[:, 3]).max() / self.nominal[:, 3].max()
        self.assertLess(rel, 0.01)

    def test_enzyme_loss_is_nonlinear(self):
        # Membrane-limited: little change at first, then a collapse once the enzyme limits flux.
        tr = trace(em.Failures(enzyme_half_life_h=8.0))
        early = self.window(tr, 6, 12) / self.window(self.nominal, 6, 12)
        late = self.window(tr, 42, 48) / self.window(self.nominal, 42, 48)
        self.assertGreater(early, 0.95)
        self.assertLess(late, 0.9)  # 0.25 by 72 h, see the stress fixtures

    def test_fouling_lowers_sensitivity_monotonically(self):
        tr = trace(em.Failures(fouling_fraction=0.6))
        r = [self.window(tr, h, h + 6) / self.window(self.nominal, h, h + 6) for h in (0, 12, 24, 42)]
        self.assertTrue(all(x > y for x, y in zip(r, r[1:])), r)
        self.assertLess(r[-1], 0.6)

    def test_reference_drift_collapses_plateau(self):
        tr = trace(em.Failures(ref_drift_mV_per_h=-6.0))
        self.assertGreater(self.window(tr, 0, 6) / self.window(self.nominal, 0, 6), 0.95)
        self.assertLess(self.window(tr, 42, 48) / self.window(self.nominal, 42, 48), 0.45)

    def test_o2_dip_is_transient(self):
        tr = trace(em.Failures(o2_dips=((30.0, 0.7, 0.003),)))
        self.assertLess(self.window(tr, 30.2, 30.6) / self.window(self.nominal, 30.2, 30.6), 0.4)
        self.assertAlmostEqual(self.window(tr, 33, 36) / self.window(self.nominal, 33, 36), 1.0, delta=0.03)


class Fixtures(unittest.TestCase):
    def test_rz_fixture_matches_csv(self):
        rz = stress_fixtures.RZ_PATH.read_text()
        out = Path(__file__).parent / "out"
        for name in em.STRESS_VARIANTS:
            body = re.search(rf"fn {name}_current_pa\(\) -> array \{{\s*return \[([^\]]*)\]", rz).group(1)
            pa = np.array([int(v) for v in body.split(",")])
            csv = np.loadtxt(out / f"synthetic_trace_{name}.csv", delimiter=",", skiprows=1)
            np.testing.assert_allclose(pa, np.round(csv[:, 3] * 1000), atol=1)  # CSV keeps 4 decimals


if __name__ == "__main__":
    unittest.main()
