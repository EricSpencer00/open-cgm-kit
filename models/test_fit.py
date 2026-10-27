"""Round trip: synthetic bench data from known membrane permeabilities, with noise, must be recovered."""
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np

import electrode_model as em
import fit

TRUTH = {"glucose": 0.0015, "oxygen": 0.35, "acetaminophen": 0.012}  # preset is 0.003 / 0.2 / 0.03


def bench_design() -> fit.Data:
    rows = []
    for o2 in (0.26, 0.05):
        rows += [(g, o2, 0.0) for g in (0, 2, 5, 10, 15, 20, 30)]
    rows += [(0, 0.26, 0.13), (5, 0.26, 0.13)]  # acetaminophen spike
    g, o, a = map(np.array, zip(*rows))
    return fit.Data(g.astype(float), o, a, np.zeros(len(g)), np.zeros(len(g)))


def synthetic(noise_rel=0.02, noise_abs=0.3, seed=3, enzyme=None) -> fit.Data:
    d = bench_design()
    sensor = fit.with_membrane(em.PRESETS["gox_pu"], TRUTH, enzyme)
    clean = fit.predict(sensor, em.BEAKER, d)
    sigma = np.hypot(noise_rel * clean, noise_abs)
    noisy = clean + np.random.default_rng(seed).normal(0, 1, clean.size) * sigma
    return replace(d, current_nA=noisy, sigma_nA=sigma)


class Fit(unittest.TestCase):
    def test_recovers_permeabilities_within_10_percent(self):
        res = fit.fit(synthetic())
        self.assertTrue(res["success"])
        for s, true in TRUTH.items():
            p = res["params"][s]
            self.assertAlmostEqual(p["value"] / true, 1.0, delta=0.10, msg=s)
            self.assertLess(p["ci95_factor"], 1.3, s)
        self.assertLess(res["chi2_per_dof"], 3)

    def test_csv_round_trip_and_cli_format(self):
        d = synthetic(seed=5)
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "bench.csv"
            fit.write_csv(path, d, "synthetic")
            back = fit.read_csv(path)
        np.testing.assert_allclose(back.current_nA, d.current_nA, rtol=1e-4)

    def test_enzyme_unidentifiable_when_membrane_limited(self):
        # The membrane limits flux, so loading cannot be fitted: the interval must say so.
        res = fit.fit(synthetic(enzyme=1.0), fit_enzyme=True)
        self.assertGreater(res["params"]["enzyme_u_per_cm2"]["ci95_factor"], 3)


if __name__ == "__main__":
    unittest.main()
