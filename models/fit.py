"""Fit the outer membrane's glucose, O2 and acetaminophen permeabilities to bench data.

    python3 electrode_model.py fit data.csv [--preset gox_pu] [--fit-enzyme] [--out fit.json]

Input CSV: one steady-state current per row, comment lines start with '#'.

    glucose_mM,oxygen_mM,acetaminophen_mM,current_nA[,sigma_nA]

A usable set is a glucose calibration at two O2 levels (for example air-saturated
0.26 mM and N2-sparged ~0.05 mM, O2 measured by a probe) plus one acetaminophen
spike: the same glucose and O2 with and without added acetaminophen (a 0 mM
glucose row with acetaminophen is the cleanest). Subtract nothing; the model
includes the acetaminophen current. `sigma_nA` is optional; without it the
standard error is 3 % of the reading plus 0.3 nA.

Fitted: log10 permeability D*K (relative to water) of the outer membrane for glucose,
oxygen and acetaminophen, optionally GOx loading (U/cm2). Everything else (layer
thicknesses, peroxide permeability, Km, temperature, stagnant layer) comes from the
preset and flags and is held fixed; a wrong fixed value biases the fit. Uncertainty
is Jacobian-based (Gauss-Newton covariance scaled by the residual chi2/dof) and
reported as a multiplicative 95 % factor, plus the parameter correlation matrix.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

import electrode_model as em

PERM_SPECIES = ("glucose", "oxygen", "acetaminophen")


@dataclass(frozen=True)
class Data:
    glucose_mM: np.ndarray
    oxygen_mM: np.ndarray
    acetaminophen_mM: np.ndarray
    current_nA: np.ndarray
    sigma_nA: np.ndarray


def read_csv(path) -> Data:
    lines = [l for l in Path(path).read_text().splitlines() if l.strip() and not l.lstrip().startswith("#")]
    rows = list(csv.DictReader(lines))
    need = ("glucose_mM", "oxygen_mM", "acetaminophen_mM", "current_nA")
    if not rows or any(k not in rows[0] for k in need):
        raise ValueError(f"CSV needs columns {','.join(need)}[,sigma_nA]")
    col = lambda k: np.array([float(r[k]) for r in rows])
    cur = col("current_nA")
    sigma = col("sigma_nA") if "sigma_nA" in rows[0] else np.hypot(0.03 * np.abs(cur), 0.3)
    return Data(col("glucose_mM"), col("oxygen_mM"), col("acetaminophen_mM"), cur, sigma)


def write_csv(path, data: Data, comment: str = ""):
    with open(path, "w") as f:
        if comment:
            f.write(f"# {comment}\n")
        f.write("glucose_mM,oxygen_mM,acetaminophen_mM,current_nA,sigma_nA\n")
        for row in zip(data.glucose_mM, data.oxygen_mM, data.acetaminophen_mM, data.current_nA, data.sigma_nA):
            f.write(",".join(f"{v:.5g}" for v in row) + "\n")


def with_membrane(sensor: em.Sensor, perm: dict[str, float], enzyme_u_per_cm2: float | None = None) -> em.Sensor:
    """Set outer-membrane permeabilities D*K (relative to water) by adjusting partition coefficients."""
    mem = sensor.layers[-1]
    part = dict(mem.partition)
    for s, p in perm.items():
        part[s] = p / mem.d_ratio[s]
    layers = sensor.layers[:-1] + (replace(mem, partition=part),)
    return replace(sensor, layers=layers,
                   enzyme_u_per_cm2=sensor.enzyme_u_per_cm2 if enzyme_u_per_cm2 is None else enzyme_u_per_cm2)


def membrane_perm(sensor: em.Sensor) -> dict[str, float]:
    mem = sensor.layers[-1]
    return {s: mem.d_ratio[s] * mem.k(s) for s in PERM_SPECIES}


def predict(sensor: em.Sensor, cond: em.Conditions, data: Data) -> np.ndarray:
    """Steady currents for each row; rows sharing O2 are solved in glucose order with continuation."""
    out = np.empty(len(data.current_nA))
    order = np.lexsort((data.glucose_mM, data.acetaminophen_mM, data.oxygen_mM))
    y, last = None, None
    for i in order:
        key = (data.oxygen_mM[i], data.acetaminophen_mM[i])
        if key != last:
            y, last = None, key
        c = replace(cond, glucose_mM=float(data.glucose_mM[i]), oxygen_mM=float(data.oxygen_mM[i]),
                    acetaminophen_mM=float(data.acetaminophen_mM[i]))
        m = em.Model(sensor, c)
        y = m.steady(y0=y)
        out[i] = m.total_nA(y)
    return out


def fit(data: Data, sensor: em.Sensor | None = None, cond: em.Conditions | None = None,
        fit_enzyme: bool = False, start: dict[str, float] | None = None) -> dict:
    sensor = sensor or em.PRESETS["gox_pu"]
    cond = cond or em.BEAKER
    p0 = start or membrane_perm(sensor)
    names = list(PERM_SPECIES) + (["enzyme_u_per_cm2"] if fit_enzyme else [])
    x0 = np.log10([p0[s] if s in p0 else sensor.enzyme_u_per_cm2 for s in names])

    def build(x):
        v = dict(zip(names, 10.0 ** x))
        return with_membrane(sensor, {s: v[s] for s in PERM_SPECIES}, v.get("enzyme_u_per_cm2"))

    def resid(x):
        return (predict(build(x), cond, data) - data.current_nA) / data.sigma_nA

    lo = np.array([-6.0] * 3 + [-3.0] * fit_enzyme)
    hi = np.array([1.0] * 3 + [3.0] * fit_enzyme)
    sol = least_squares(resid, x0, bounds=(lo, hi), diff_step=1e-3, x_scale=1.0)
    dof = len(data.current_nA) - len(names)
    chi2 = float(2 * sol.cost)
    scale = max(chi2 / dof, 1.0) if dof > 0 else 1.0  # never trust errors smaller than the stated sigma
    jtj = sol.jac.T @ sol.jac
    cov = np.linalg.pinv(jtj) * scale
    se = np.sqrt(np.clip(np.diag(cov), 0, None))  # in log10 units
    sv = np.linalg.svd(sol.jac, compute_uv=False)
    corr = cov / np.outer(se, se) if np.all(se > 0) else np.full_like(cov, np.nan)
    params = {}
    for n, xi, s in zip(names, sol.x, se):
        params[n] = {"value": float(10 ** xi), "log10_se": float(s),
                     "ci95_factor": float(10 ** (1.96 * s)),
                     "ci95": [float(10 ** (xi - 1.96 * s)), float(10 ** (xi + 1.96 * s))]}
    return {
        "preset": sensor,
        "params": params,
        "chi2_per_dof": chi2 / dof if dof > 0 else float("nan"),
        "rmse_nA": float(np.sqrt(np.mean((resid(sol.x) * data.sigma_nA) ** 2))),
        "n": len(data.current_nA),
        "jacobian_condition": float(sv[0] / sv[-1]) if sv[-1] > 0 else float("inf"),
        "correlation": corr.tolist(),
        "names": names,
        "success": bool(sol.success),
        "predicted_nA": predict(build(sol.x), cond, data).tolist(),
    }


def run(args) -> dict:
    data = read_csv(args.csv)
    sensor = em.PRESETS[args.preset]
    cond = replace(em.BEAKER, temp_c=args.temp_c, boundary_um=args.boundary_um)
    res = fit(data, sensor, cond, fit_enzyme=args.fit_enzyme)
    res["preset"] = args.preset
    print(f"{'parameter':18s} {'value':>10s}   95 % interval")
    for n, p in res["params"].items():
        print(f"{n:18s} {p['value']:10.3g}   {p['ci95'][0]:.3g} .. {p['ci95'][1]:.3g}  (x/÷ {p['ci95_factor']:.2f})")
    print(f"chi2/dof {res['chi2_per_dof']:.2f}  rmse {res['rmse_nA']:.3g} nA  "
          f"Jacobian condition {res['jacobian_condition']:.3g}  converged {res['success']}")
    if args.out:
        Path(args.out).write_text(json.dumps(res, indent=2) + "\n")
    return res
