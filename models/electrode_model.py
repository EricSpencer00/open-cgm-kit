"""In-silico model of a first-generation glucose oxidase (GOx) amperometric electrode.

One-dimensional reaction-diffusion through a planar layer stack, solved by the
finite-volume method of lines:

    electrode | [inner layer] | enzyme layer | [outer membrane] | boundary layer | bulk

Species: glucose, oxygen, hydrogen peroxide and acetaminophen (a representative
electroactive interferent). GOx follows ping-pong kinetics in glucose and oxygen,
producing one H2O2 per glucose. The electrode consumes H2O2 (2 e-) and, at a
+0.6 V Pt bias, also oxidizes acetaminophen (2 e-). A Prussian-blue (~0 V)
electrode reduces H2O2 but leaves acetaminophen alone.

The physics is standard; most parameter values are literature-range guesses.
Each layer has a diffusivity and a partition coefficient K per species; the
solver state is the bulk-equivalent concentration u = c/K, continuous across
interfaces, so steady flux depends on permeability D*K while response time also
depends on D alone.

Use this for scaling, trade-offs and deciding what to measure, not as a
prediction of a particular coating. Units: mM == mol/m^3, lengths in m inside
the solver.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import lil_matrix

F = 96485.332  # C/mol
SPECIES = ("glucose", "oxygen", "peroxide", "acetaminophen")
G, O, P, A = range(len(SPECIES))

# Aqueous diffusivities at 25 C, m^2/s.
WATER_D_25C = {"glucose": 6.7e-10, "oxygen": 2.1e-9, "peroxide": 1.4e-9, "acetaminophen": 6.5e-10}

# Water viscosity (mPa s) for Stokes-Einstein temperature scaling.
_WATER_VISCOSITY = {25.0: 0.890, 37.0: 0.692}


def water_d(temp_c: float = 25.0) -> dict[str, float]:
    eta = np.interp(temp_c, list(_WATER_VISCOSITY), list(_WATER_VISCOSITY.values()))
    scale = ((temp_c + 273.15) / 298.15) * (_WATER_VISCOSITY[25.0] / eta)
    return {s: d * scale for s, d in WATER_D_25C.items()}


@dataclass(frozen=True)
class Layer:
    name: str
    thickness_um: float
    d_ratio: dict[str, float]  # diffusivity relative to water at the same temperature
    enzyme: bool = False
    cells: int = 30
    partition: dict[str, float] = field(default_factory=dict)  # layer/water, default 1

    def k(self, species: str) -> float:
        return self.partition.get(species, 1.0)


@dataclass(frozen=True)
class Sensor:
    layers: tuple[Layer, ...]
    area_mm2: float = math.pi * 0.6**2  # A0 1.2 mm Pt disk
    enzyme_u_per_cm2: float = 1.0  # active GOx after immobilization, umol/min/cm^2
    km_glucose_mM: float = 30.0
    km_oxygen_mM: float = 0.25
    mode: str = "pt"  # "pt" (+0.6 V vs Ag/AgCl) or "pb" (Prussian blue, ~0 V)

    @property
    def enzyme_thickness_m(self) -> float:
        return sum(l.thickness_um for l in self.layers if l.enzyme) * 1e-6

    @property
    def vmax_mM_per_s(self) -> float:
        mol_per_m2_s = self.enzyme_u_per_cm2 * 1e-6 / 60 / 1e-4
        return mol_per_m2_s / self.enzyme_thickness_m


@dataclass(frozen=True)
class Conditions:
    glucose_mM: float = 5.0
    oxygen_mM: float = 0.26  # air-saturated buffer, 25 C
    acetaminophen_mM: float = 0.0
    peroxide_mM: float = 0.0  # bulk H2O2, used for transducer checks
    temp_c: float = 25.0
    boundary_um: float = 50.0  # stagnant layer; ~20-100 um stirred, larger quiescent
    boundary_d_ratio: float = 1.0  # 1 for buffer; ~0.3-0.5 for tissue

    def bulk(self) -> np.ndarray:
        return np.array([self.glucose_mM, self.oxygen_mM, self.peroxide_mM, self.acetaminophen_mM])


def _hydrogel(cells=20) -> Layer:
    return Layer("GOx/BSA/glutaraldehyde", 5.0, {s: 0.5 for s in SPECIES}, enzyme=True, cells=cells)


# Illustrative presets. The outer-membrane permeabilities are the dominant
# unknowns and must be fitted from measurements (see SENSOR_PROCESS.md).
PRESETS = {
    "bare_gox": Sensor(layers=(_hydrogel(),)),
    "gox_pu": Sensor(
        layers=(
            _hydrogel(),
            Layer(
                "polyurethane outer membrane",
                15.0,
                {"glucose": 0.1, "oxygen": 0.1, "peroxide": 0.1, "acetaminophen": 0.1},
                cells=30,
                # Permeability ratios D*K: glucose 0.003, O2 0.2, H2O2 0.03, APAP 0.03.
                partition={"glucose": 0.03, "oxygen": 2.0, "peroxide": 0.3, "acetaminophen": 0.3},
            ),
        )
    ),
}
# Tighter glucose barrier (permeability 3e-4, O2:glucose ~670) needed for linearity at tissue O2.
PRESETS["gox_pu_tissue"] = replace(
    PRESETS["gox_pu"],
    layers=(PRESETS["gox_pu"].layers[0],
            replace(PRESETS["gox_pu"].layers[1], partition={"glucose": 0.003, "oxygen": 2.0, "peroxide": 0.3,
                                                            "acetaminophen": 0.03})),
)
PRESETS["pb_gox_pu"] = replace(PRESETS["gox_pu"], mode="pb")
PRESETS["dropsens_4mm_gox_pu"] = replace(PRESETS["gox_pu"], area_mm2=math.pi * 2.0**2)
BEAKER = Conditions()
# Interstitial-fluid-like: 37 C, ~40 mmHg O2, diffusion through ~100 um of tissue.
TISSUE = Conditions(oxygen_mM=0.06, temp_c=37.0, boundary_um=100.0, boundary_d_ratio=0.4)


@dataclass
class Grid:
    h: np.ndarray  # cell widths (m)
    k: np.ndarray  # (species, cells) partition coefficients
    g_face: np.ndarray  # (species, cells+1) face conductances D/dx (m/s)
    enzyme: np.ndarray  # bool per cell
    sink: np.ndarray  # bool per species: consumed at the electrode
    x_mid: np.ndarray = field(default=None)


def build_grid(sensor: Sensor, cond: Conditions) -> Grid:
    wd = water_d(cond.temp_c)
    layers = list(sensor.layers) + [
        Layer("boundary", cond.boundary_um, {s: cond.boundary_d_ratio for s in SPECIES}, cells=30)
    ]
    h, d, k, enz = [], [], [], []
    for layer in layers:
        # Geometric refinement toward both layer edges keeps thin films resolved.
        t = np.linspace(0, 1, layer.cells + 1)
        edges = layer.thickness_um * 1e-6 * (0.5 - 0.5 * np.cos(np.pi * t))
        widths = np.diff(edges)
        h.extend(widths)
        d.extend([[wd[s] * layer.d_ratio[s] for s in SPECIES]] * layer.cells)
        k.extend([[layer.k(s) for s in SPECIES]] * layer.cells)
        enz.extend([layer.enzyme] * layer.cells)
    h = np.array(h)
    k = np.array(k).T  # (species, cells)
    half = h / 2 / (np.array(d).T * k)  # half-cell resistance to u = c/K
    g = np.empty((len(SPECIES), len(h) + 1))
    g[:, 0] = 1 / half[:, 0]
    g[:, 1:-1] = 1 / (half[:, :-1] + half[:, 1:])
    g[:, -1] = 1 / half[:, -1]
    sink = np.array([False, False, True, sensor.mode == "pt"])
    x_mid = np.cumsum(h) - h / 2
    return Grid(h=h, k=k, g_face=g, enzyme=np.array(enz), sink=sink, x_mid=x_mid)


class Model:
    def __init__(self, sensor: Sensor, cond: Conditions):
        self.sensor, self.cond = sensor, cond
        self.grid = build_grid(sensor, cond)
        self.n = len(self.grid.h)
        self.bulk = cond.bulk()
        self.vmax = sensor.vmax_mM_per_s
        self._sparsity = self._jac_sparsity()

    def _jac_sparsity(self):
        n, ns = self.n, len(SPECIES)
        m = lil_matrix((ns * n, ns * n), dtype=int)
        for s in range(ns):
            for i in range(n):
                for j in (i - 1, i, i + 1):
                    if 0 <= j < n:
                        m[s * n + i, s * n + j] = 1
        for i in np.flatnonzero(self.grid.enzyme):
            for s in (G, O, P):
                for t in (G, O):
                    m[s * n + i, t * n + i] = 1
        return m.tocsr()

    def rate(self, u: np.ndarray) -> np.ndarray:
        """Volumetric GOx rate from the solver state u = c/K."""
        g = np.clip(u[G] * self.grid.k[G], 0, None)
        o = np.clip(u[O] * self.grid.k[O], 0, None)
        s = self.sensor
        denom = g * o + s.km_glucose_mM * o + s.km_oxygen_mM * g
        r = np.where(denom > 0, self.vmax * g * o / np.where(denom > 0, denom, 1), 0.0)
        return r * self.grid.enzyme

    def rhs(self, _t, y, bulk=None):
        bulk = self.bulk if bulk is None else bulk
        c = y.reshape(len(SPECIES), self.n)
        gf = self.grid.g_face
        flux = np.empty((len(SPECIES), self.n + 1))  # +x direction, mol/m^2/s
        flux[:, 0] = np.where(self.grid.sink, -gf[:, 0] * c[:, 0], 0.0)
        flux[:, 1:-1] = -gf[:, 1:-1] * np.diff(c, axis=1)
        flux[:, -1] = -gf[:, -1] * (bulk - c[:, -1])
        dc = flux[:, :-1] - flux[:, 1:] - np.outer([1, 1, -1, 0], self.rate(c)) * self.grid.h
        return (dc / (self.grid.h * self.grid.k)).ravel()

    def current_nA(self, y) -> dict[str, float]:
        c = y.reshape(len(SPECIES), self.n)
        area = self.sensor.area_mm2 * 1e-6
        to_electrode = self.grid.g_face[:, 0] * c[:, 0] * self.grid.sink
        return {
            "peroxide": 2 * F * to_electrode[P] * area * 1e9,
            "acetaminophen": 2 * F * to_electrode[A] * area * 1e9,
        }

    def total_nA(self, y) -> float:
        return sum(self.current_nA(y).values())

    def initial(self) -> np.ndarray:
        return np.repeat(self.bulk[:, None], self.n, axis=1).ravel()

    def _integrate(self, y0, t_end, bulk=None, t_eval=None):
        return solve_ivp(
            self.rhs, (0, t_end), y0, method="BDF", jac_sparsity=self._sparsity,
            rtol=1e-6, atol=1e-12, t_eval=t_eval, args=(bulk,),
        )

    def steady(self, y0=None, bulk=None) -> np.ndarray:
        y = self.initial() if y0 is None else y0
        for t_end in (600, 6000, 60000):
            sol = self._integrate(y, t_end, bulk)
            if not sol.success:
                raise RuntimeError(sol.message)
            y = sol.y[:, -1]
            rel = np.abs(self.rhs(0, y, bulk)) * t_end / (np.abs(y) + 1e-9)
            if rel.max() < 1e-3:
                return y
        raise RuntimeError("steady state not reached")

    def step(self, y0, new_bulk, t_end=1800, points=600):
        t_eval = np.linspace(0, t_end, points)
        sol = self._integrate(y0, t_end, new_bulk, t_eval)
        currents = np.array([self.total_nA(sol.y[:, k]) for k in range(sol.y.shape[1])])
        return sol.t, currents


def calibration(sensor: Sensor, cond: Conditions, glucose_mM) -> np.ndarray:
    """Steady current (nA) at each glucose concentration, using continuation."""
    out, y = [], None
    for gmM in glucose_mM:
        m = Model(sensor, replace(cond, glucose_mM=float(gmM)))
        y = m.steady(y0=y)
        out.append(m.total_nA(y))
    return np.array(out)


def linear_limit_mM(conc, current, tol=0.10) -> float:
    """Highest concentration whose current is within tol of the low-concentration slope."""
    slope = (current[1] - current[0]) / (conc[1] - conc[0])
    ideal = current[0] + slope * (np.asarray(conc) - conc[0])
    ok = np.abs(current - ideal) <= tol * np.abs(ideal - current[0]) + 1e-15
    limit = conc[0]
    for c, good in zip(conc[1:], ok[1:]):
        if not good:
            break
        limit = c
    return float(limit)


def t90_s(t, i) -> float:
    i0, i1 = i[0], i[-1]
    target = i0 + 0.9 * (i1 - i0)
    crossed = np.flatnonzero((i - target) * np.sign(i1 - i0) >= 0)
    return float(t[crossed[0]]) if crossed.size else float("nan")


# AD5940 readout as configured by the pinned Biocoin CA technique
# (echem_ca.cpp, ad5940.c AD5940_ADCCode2Volt): 16-bit, Vref 1.82 V, PGA 1.5.
ADC_VREF, ADC_PGA = 1.82, 1.5
RTIA_OPTIONS_OHM = {"10K": 10e3, "20K": 20e3, "40K": 40e3, "80K": 80e3, "160K": 160e3, "512K": 512e3}


def readout(max_nA: float, sens_nA_per_mM: float) -> list[dict]:
    rows = []
    for name, r in RTIA_OPTIONS_OHM.items():
        lsb_nA = ADC_VREF / ADC_PGA / 32768 / r * 1e9
        full_nA = ADC_VREF / ADC_PGA / r * 1e9 * 0.8  # keep 20% headroom
        rows.append({
            "rtia": name,
            "lsb_nA": lsb_nA,
            "usable_full_scale_nA": full_nA,
            "lsb_glucose_mM": lsb_nA / sens_nA_per_mM if sens_nA_per_mM > 0 else float("inf"),
            "fits": bool(max_nA <= full_nA),
        })
    return rows


def characterize(name: str, sensor: Sensor) -> dict:
    conc = np.array([0, 1, 2, 4, 6, 8, 10, 12.5, 15, 20, 25, 30], dtype=float)
    beaker = calibration(sensor, BEAKER, conc)
    tissue = calibration(sensor, TISSUE, conc)
    sens = float(np.polyfit(conc[:5], beaker[:5], 1)[0])
    sens_t = float(np.polyfit(conc[:5], tissue[:5], 1)[0])

    m = Model(sensor, replace(BEAKER, glucose_mM=5.0))
    y5 = m.steady()
    t, i = m.step(y5, replace(BEAKER, glucose_mM=10.0).bulk())

    ap = replace(BEAKER, glucose_mM=5.0, acetaminophen_mM=0.13)  # ~20 mg/L therapeutic
    ma = Model(sensor, ap)
    i_ap = ma.current_nA(ma.steady())["acetaminophen"]

    rows = readout(max(beaker.max(), tissue.max()), sens_t)
    best = next((r for r in reversed(rows) if r["fits"]), rows[0])
    return {
        "name": name,
        "mode": sensor.mode,
        "area_mm2": round(sensor.area_mm2, 3),
        "beaker": {
            "sensitivity_nA_per_mM": sens,
            "linear_to_mM": linear_limit_mM(conc, beaker),
            "current_at_25mM_nA": float(np.interp(25, conc, beaker)),
            "t90_5_to_10mM_s": t90_s(t, i),
        },
        "tissue": {
            "sensitivity_nA_per_mM": sens_t,
            "linear_to_mM": linear_limit_mM(conc, tissue),
            "current_at_25mM_nA": float(np.interp(25, conc, tissue)),
        },
        "acetaminophen_0p13mM_glucose_equiv_mM": i_ap / sens if sens > 0 else float("nan"),
        "readout": rows,
        "recommended_rtia": best["rtia"],
        "_curves": {"conc": conc.tolist(), "beaker": beaker.tolist(), "tissue": tissue.tolist(),
                    "step_t": t.tolist(), "step_i": i.tolist()},
    }


# Monte Carlo over literature-plausible ranges (log-uniform).
MC_RANGES = {
    "enzyme_u_per_cm2": (0.1, 10.0),
    "km_glucose_mM": (10.0, 60.0),
    "km_oxygen_mM": (0.1, 0.6),
    "membrane_um": (5.0, 30.0),
    "membrane_glucose_ratio": (3e-4, 1e-2),  # permeability D*K relative to water
    "membrane_d_ratio": (0.02, 0.3),
    "membrane_oxygen_ratio": (0.05, 0.5),
    "membrane_ap_over_glucose": (1.0, 30.0),
    "boundary_um": (20.0, 150.0),
}


def mc_sensor(p: dict) -> tuple[Sensor, Conditions]:
    base = PRESETS["gox_pu"]
    perm = {"glucose": p["membrane_glucose_ratio"], "oxygen": p["membrane_oxygen_ratio"], "peroxide": 0.03,
            "acetaminophen": p["membrane_glucose_ratio"] * p["membrane_ap_over_glucose"]}
    dr = p["membrane_d_ratio"]
    mem = Layer("outer membrane", p["membrane_um"], {s: dr for s in SPECIES}, cells=30,
                partition={s: v / dr for s, v in perm.items()})
    sensor = replace(base, layers=(base.layers[0], mem), enzyme_u_per_cm2=p["enzyme_u_per_cm2"],
                     km_glucose_mM=p["km_glucose_mM"], km_oxygen_mM=p["km_oxygen_mM"])
    return sensor, replace(BEAKER, boundary_um=p["boundary_um"])


def monte_carlo(n: int, seed: int = 0) -> dict:
    from scipy.stats import spearmanr

    rng = np.random.default_rng(seed)
    conc = np.array([0, 2, 5, 10, 15, 20, 25], dtype=float)
    samples, metrics = [], []
    for _ in range(n):
        p = {k: float(math.exp(rng.uniform(math.log(lo), math.log(hi)))) for k, (lo, hi) in MC_RANGES.items()}
        sensor, beaker = mc_sensor(p)
        tissue = replace(TISSUE)
        try:
            ib = calibration(sensor, beaker, conc)
            it = calibration(sensor, tissue, conc)
            m = Model(sensor, replace(beaker, glucose_mM=5.0))
            y5 = m.steady()
            t, i = m.step(y5, replace(beaker, glucose_mM=10.0).bulk(), t_end=3600, points=720)
            ma = Model(sensor, replace(beaker, glucose_mM=5.0, acetaminophen_mM=0.13))
            iap = ma.current_nA(ma.steady())["acetaminophen"]
        except RuntimeError:
            continue
        sens = (ib[2] - ib[0]) / 5.0
        metrics.append({
            "sensitivity_nA_per_mM": sens,
            "tissue_linear_to_mM": linear_limit_mM(conc, it),
            "t90_s": t90_s(t, i),
            "ap_glucose_equiv_mM": iap / sens if sens > 0 else float("nan"),
        })
        samples.append(p)
    keys = list(MC_RANGES)
    summary, drivers = {}, {}
    for metric in metrics[0]:
        v = np.array([m[metric] for m in metrics])
        summary[metric] = {q: float(np.nanpercentile(v, int(q[1:]))) for q in ("p10", "p50", "p90")}
        corr = {k: float(spearmanr([s[k] for s in samples], v, nan_policy="omit")[0]) for k in keys}
        drivers[metric] = dict(sorted(corr.items(), key=lambda kv: -abs(kv[1]))[:3])
    return {"n": len(metrics), "ranges": MC_RANGES, "summary": summary, "top_drivers_spearman": drivers}


@dataclass(frozen=True)
class Failures:
    """Failure modes layered on the synthetic trace. All off by default.

    Enzyme loss, membrane fouling and O2 dips are run through the 1D model (steady-state
    curves over a grid of enzyme fraction, membrane permeability factor and tissue O2),
    so their effect on sensitivity is nonlinear: enzyme loss does nothing while the membrane
    limits flux. Reference drift is a stand-in: a logistic current plateau around +0.35 V
    (illustrative, not from the 1D model) plus a small oxidative background.
    """
    enzyme_half_life_h: float | None = None  # exponential loss of active GOx
    fouling_fraction: float = 0.0  # final fractional loss of all outer-membrane permeabilities
    fouling_tau_h: float = 30.0
    ref_drift_mV_per_h: float = 0.0  # working potential vs reference changes by this per hour (negative = falls)
    o2_dips: tuple[tuple[float, float, float], ...] = ()  # (start_h, duration_h, tissue O2 mM), 8 min ramps
    o2_ramp_h: float = 8 / 60


def _failure_interpolator(sensor: Sensor, f: Failures, hours: float):
    from scipy.interpolate import RegularGridInterpolator

    conc = np.array([0, 1, 2, 3, 4, 6, 8, 10, 12.5, 15, 20, 25, 30], dtype=float)
    pair = lambda lo, hi: np.array([lo, hi if hi > lo else lo * 1.001])
    e_ax = (np.array([1, .5, .25, .12, .06, .03, .015, .008])[::-1]
            if f.enzyme_half_life_h else pair(1.0, 1.0))
    p_ax = np.array([0.4, 0.6, 0.8, 1.0]) if f.fouling_fraction else pair(1.0, 1.0)
    o_ax = np.array(sorted({TISSUE.oxygen_mM, *[d[2] for d in f.o2_dips]})) if f.o2_dips else pair(TISSUE.oxygen_mM, TISSUE.oxygen_mM)
    if f.enzyme_half_life_h:
        e_ax = e_ax[e_ax >= 0.5 ** (hours / f.enzyme_half_life_h) * 0.9]
        e_ax = np.unique(np.append(e_ax, [e_ax.min() * 0.5, 1.0]))
    if f.fouling_fraction:
        p_ax = np.unique(np.append(np.linspace(1 - f.fouling_fraction, 1.0, 4), 1.0))
    vals = np.empty((len(e_ax), len(p_ax), len(o_ax), len(conc)))
    mem = sensor.layers[-1]
    for i, e in enumerate(e_ax):
        for j, p in enumerate(p_ax):
            part = {s_: mem.k(s_) * p for s_ in SPECIES}
            fouled = replace(sensor, enzyme_u_per_cm2=sensor.enzyme_u_per_cm2 * e,
                             layers=sensor.layers[:-1] + (replace(mem, partition=part),))
            for k, o2 in enumerate(o_ax):
                vals[i, j, k] = calibration(fouled, replace(TISSUE, oxygen_mM=float(o2)), conc)
    return RegularGridInterpolator((np.log10(e_ax), np.log10(p_ax), o_ax, conc), vals, bounds_error=False, fill_value=None)


def tissue_o2_profile(t_h: np.ndarray, f: Failures) -> np.ndarray:
    o2 = np.full_like(t_h, TISSUE.oxygen_mM)
    for start, dur, level in f.o2_dips:
        r = f.o2_ramp_h
        down = np.clip((t_h - start) / r, 0, 1)
        up = np.clip((t_h - (start + dur)) / r, 0, 1)
        o2 = np.minimum(o2, TISSUE.oxygen_mM + (level - TISSUE.oxygen_mM) * (down - up))
    return o2


def synthetic_trace(result: dict, hours=24.0, dt_s=60.0, rtia="160K", seed=1, failures: Failures | None = None) -> np.ndarray:
    """Plausible raw-current trace for software fixtures: meals, ISF lag, sensor lag,
    sensitivity drift, noise and ADC quantization. Not a physiological model.
    `failures` adds enzyme loss, fouling, reference drift and O2 dips (see Failures)."""
    rng = np.random.default_rng(seed)
    t = np.arange(0, hours * 3600, dt_s, dtype=float)
    blood = np.full_like(t, 5.5)
    for day in range(int(math.ceil(hours / 24))):
        for meal_h, peak in ((7.5, 4.0), (12.5, 5.0), (19.0, 6.0)):
            tm = (t / 3600 - meal_h - 24 * day)
            blood += np.where(tm > 0, peak * (tm / 0.75) * np.exp(1 - tm / 0.75), 0)
    def lag(x, tau):
        y = np.empty_like(x); y[0] = x[0]; a = dt_s / (tau + dt_s)
        for k in range(1, len(x)):
            y[k] = y[k - 1] + a * (x[k] - y[k - 1])
        return y
    isf = lag(blood, 8 * 60)
    tau = max(result["beaker"]["t90_5_to_10mM_s"], dt_s) / math.log(10)
    curves = result["_curves"]
    sensed = lag(isf, tau)
    drift = 1 - 0.05 * t / 86400
    if failures is None:
        ideal = np.interp(sensed, curves["conc"], curves["tissue"])
        noisy = ideal * drift + rng.normal(0, 0.05, t.size)
    else:
        f, th = failures, t / 3600
        interp = _failure_interpolator(PRESETS[result["name"]], f, hours)
        e = 0.5 ** (th / f.enzyme_half_life_h) if f.enzyme_half_life_h else np.ones_like(th)
        p = 1 - f.fouling_fraction * (1 - np.exp(-th / f.fouling_tau_h))
        o2 = tissue_o2_profile(th, f)
        pts = np.column_stack([np.log10(e), np.log10(p), o2, np.clip(sensed, 0, 30)])
        ideal = interp(pts)
        e_mV = 600.0 + f.ref_drift_mV_per_h * th
        plateau = 1 / (1 + np.exp((350.0 - e_mV) / 35.0)) / (1 / (1 + np.exp((350.0 - 600.0) / 35.0)))
        background = 0.05 * np.clip((e_mV - 600.0) / 100.0, 0, None)  # nA
        noisy = ideal * drift * plateau + background + rng.normal(0, 0.05, t.size)
    lsb = ADC_VREF / ADC_PGA / 32768 / RTIA_OPTIONS_OHM[rtia] * 1e9
    raw = np.round(noisy / lsb) * lsb
    return np.column_stack([t, blood, isf, raw])


STRESS_HOURS, STRESS_DT_S = 72.0, 300.0
STRESS_VARIANTS = {
    "nominal": None,
    "enzyme_loss": Failures(enzyme_half_life_h=8.0),
    "fouling": Failures(fouling_fraction=0.6),
    "reference_drift": Failures(ref_drift_mV_per_h=-6.0),
    "o2_dips": Failures(o2_dips=((30.0, 0.7, 0.003), (61.0, 0.5, 0.004))),
}


def stress_traces(result: dict) -> dict[str, np.ndarray]:
    """72 h, 5 min traces for each failure mode on the tissue-grade membrane, 512 kohm gain."""
    return {name: synthetic_trace(result, STRESS_HOURS, STRESS_DT_S, "512K", seed=7, failures=f)
            for name, f in STRESS_VARIANTS.items()}


def plot(results: list[dict], out: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
    for r in results:
        c = r["_curves"]
        conc = np.array(c["conc"])
        style = {"ls": "--" if r["mode"] == "pb" else "-", "marker": "o", "ms": 3, "label": r["name"]}
        for a, key in ((ax[0], "beaker"), (ax[1], "tissue")):
            i = np.array(c[key])
            apparent = (i - i[0]) / ((i[1] - i[0]) / (conc[1] - conc[0]))  # read with low-range slope
            a.plot(conc, apparent, **style)
        i = np.array(c["step_i"])
        ax[2].plot(c["step_t"], (i - i[0]) / (i[-1] - i[0]), ls=style["ls"], label=r["name"])
    for a, title in ((ax[0], "Beaker: 25 C, air-saturated O2"), (ax[1], "Tissue-like: 37 C, 0.06 mM O2")):
        a.plot([0, 30], [0, 30], color="0.6", lw=1, zorder=0)
        a.set(title=title, xlabel="true glucose (mM)", ylabel="apparent glucose, low-range slope (mM)",
              xlim=(0, 30), ylim=(0, 32))
    ax[2].set(title="Step 5 -> 10 mM (beaker)", xlabel="time (s)", ylabel="normalized response", xlim=(0, 60))
    for a in ax:
        a.grid(alpha=0.3)
    ax[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=130)


def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "fit":
        import fit as fit_mod
        fp = argparse.ArgumentParser(prog="electrode_model.py fit", description=fit_mod.__doc__.splitlines()[0])
        fp.add_argument("csv", type=Path)
        fp.add_argument("--preset", choices=list(PRESETS), default="gox_pu", help="fixed layer stack and starting values")
        fp.add_argument("--temp-c", type=float, default=25.0)
        fp.add_argument("--boundary-um", type=float, default=50.0)
        fp.add_argument("--fit-enzyme", action="store_true", help="also fit GOx loading (U/cm2)")
        fp.add_argument("--out", type=Path, help="write full result JSON")
        fit_mod.run(fp.parse_args(sys.argv[2:]))
        return
    if len(sys.argv) > 1 and sys.argv[1] == "stress":
        import stress_fixtures
        out = Path(__file__).parent / "out"
        result = characterize("gox_pu_tissue", PRESETS["gox_pu_tissue"])
        traces = stress_traces(result)
        stress_fixtures.write_outputs(traces, result, out)
        print(f"wrote {len(traces)} traces to {out} and {stress_fixtures.RZ_PATH}")
        return
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "out")
    ap.add_argument("--mc", type=int, default=0, help="Monte Carlo samples (0 to skip)")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    results = [characterize(name, s) for name, s in PRESETS.items()]
    report = {"presets": [{k: v for k, v in r.items() if not k.startswith("_")} for r in results]}
    if args.mc:
        report["monte_carlo"] = monte_carlo(args.mc)
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    plot(results, args.out / "model.png")

    trace = synthetic_trace(next(r for r in results if r["name"] == "gox_pu"))
    np.savetxt(args.out / "synthetic_trace_gox_pu.csv", trace, delimiter=",", fmt="%.4f",
               header="t_s,blood_glucose_mM,isf_glucose_mM,raw_current_nA", comments="")

    for r in report["presets"]:
        b, t = r["beaker"], r["tissue"]
        print(f"{r['name']:22s} {b['sensitivity_nA_per_mM']:9.2f} nA/mM  beaker linear<= {b['linear_to_mM']:5.1f} mM"
              f"  tissue linear<= {t['linear_to_mM']:5.1f} mM  t90 {b['t90_5_to_10mM_s']:6.0f} s"
              f"  APAP err {r['acetaminophen_0p13mM_glucose_equiv_mM']:5.2f} mM  RTIA {r['recommended_rtia']}")
    if args.mc:
        print(json.dumps(report["monte_carlo"]["summary"], indent=1))
        print(json.dumps(report["monte_carlo"]["top_drivers_spearman"], indent=1))


if __name__ == "__main__":
    main()
