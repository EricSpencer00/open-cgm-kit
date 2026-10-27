"""2D/3D checks of the A0 electrode layout (mechanical/parameters.json) against the 1D model.

Three questions, one steady finite-volume solver (axisymmetric r-z or planar x-z):

1. Edge effect. Peroxide made in the coating spreads sideways to the 1.2 mm Pt disk and the
   disk rim sees more flux than the centre. The 1D model ignores this; how large is the error?
2. Crosstalk. Peroxide that escapes the WE can reach the Pt counter electrode (reduced there,
   adding a current) and the Ag/AgCl reference. Axisymmetric (WE disk alone, nominal) and
   planar cross-section through all three electrodes (WE as an infinite strip: upper bound).
3. IR drop. Current WE -> CE through the electrolyte develops a potential between WE and RE.
   Solved in 3D (disk, 1.4x6 mm CE, 1.2x3 mm RE) because the CE is a strip, not a ring.

Glucose and O2 are laterally uniform whenever the coating is, and peroxide does not feed back
on them, so the glucose/O2 steady state comes from the 1D model and only the linear peroxide
and acetaminophen problems are solved in 2D. Limits: coating edges, electrode double layers
and migration are not modelled; the coating is assumed ionically transparent for IR.

    python3 geometry_2d.py        # writes out/geometry_2d.json and out/geometry_2d.png
"""
from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import cg, spsolve

import electrode_model as em

PARAMS = json.loads((Path(__file__).parent.parent / "mechanical" / "parameters.json").read_text())["coupon"]
WE, RE, CE = (PARAMS[k] for k in ("working_electrode", "reference_electrode", "counter_electrode"))
A0_RADIUS_M = WE["diameter"] / 2 * 1e-3
KAPPA_PBS = 1.5  # S/m, 1x PBS ~25 C (about 1.6 at 37 C; interstitial fluid ~1.2-1.5)


# ---------------------------------------------------------------- grids
def cosine_edges(a, b, n):
    """Cells clustered toward both ends of [a, b]."""
    return a + (b - a) * (1 - np.cos(np.pi * np.linspace(0, 1, n + 1))) / 2


def one_sided_edges(a, b, n):
    """Cells clustered toward a, coarse toward b."""
    return a + (b - a) * (1 - np.cos(np.pi / 2 * np.linspace(0, 1, n + 1)))


def join(*segments):
    out = [segments[0]]
    for s in segments[1:]:
        out.append(s[1:])
    return np.concatenate(out)


def segmented_edges(breaks, cell_m):
    """Cosine-clustered segments between breakpoints, ~cell_m average size (min 6 cells)."""
    return join(*[cosine_edges(a, b, max(6, int(round((b - a) / cell_m)))) for a, b in zip(breaks[:-1], breaks[1:])])


# ---------------------------------------------------------------- 2D steady solver
def solve_steady(x, z, perm, source, axisym, bottom, top_u, outer_u=None):
    """Steady  div(P grad u) + S = 0  on a tensor grid, u = c/K, P = D*K (m^2/s).

    x: r or planar x edges (m); z: height edges (m); perm, source: (nz, nx) arrays (S in mol/m^3/s).
    bottom: list of (area_fraction[nx], u_value) Dirichlet electrodes on z=0 (insulating elsewhere).
    top_u: Dirichlet at z=top. outer_u: Dirichlet at x=max (None: no flux). Axisymmetric uses
    volumes per radian-integrated area (full 2*pi), planar per metre of depth.
    Returns u and the molar flow (mol/s, or mol/s/m planar) into each bottom electrode.
    """
    nz, nx = perm.shape
    dx, dz = np.diff(x), np.diff(z)
    xc = (x[1:] + x[:-1]) / 2
    if axisym:
        az = math.pi * (x[1:] ** 2 - x[:-1] ** 2)  # cell footprint
        # radial half-resistances (exact for a 1/r profile)
        rl = np.log(np.where(x[:-1] > 0, xc / np.maximum(x[:-1], 1e-30), 1.0))  # centre -> left face (unused j=0)
        rr = np.log(x[1:] / xc)
        pref = 2 * math.pi * dz[:, None]
    else:
        az = dx
        rl = dx / 2
        rr = dx / 2
        pref = dz[:, None]
    n = nz * nx
    idx = np.arange(n).reshape(nz, nx)
    diag = np.zeros((nz, nx))
    rhs = (source * az[None, :] * dz[:, None]).astype(float)
    rows, cols, vals = [], [], []

    def link(a, b, g):
        rows.extend([a.ravel(), b.ravel()]); cols.extend([b.ravel(), a.ravel()]); vals.extend([g.ravel(), g.ravel()])

    gx = 1.0 / (rr[None, :-1] / (perm[:, :-1] * pref) + (np.log(xc[1:] / x[1:-1]) if axisym else dx[1:] / 2)[None, :] / (perm[:, 1:] * pref))
    link(idx[:, :-1], idx[:, 1:], gx)
    diag[:, :-1] += gx; diag[:, 1:] += gx
    gz = 1.0 / ((dz[:-1] / 2)[:, None] / (perm[:-1] * az[None, :]) + (dz[1:] / 2)[:, None] / (perm[1:] * az[None, :]))
    link(idx[:-1], idx[1:], gz)
    diag[:-1] += gz; diag[1:] += gz
    gtop = perm[-1] * az / (dz[-1] / 2)
    diag[-1] += gtop; rhs[-1] += gtop * top_u
    if outer_u is not None:
        gout = 1.0 / (rr[-1] / (perm[:, -1] * pref[:, 0]))
        diag[:, -1] += gout; rhs[:, -1] += gout * outer_u
    gb = []
    for frac, val in bottom:
        g = perm[0] * az * frac / (dz[0] / 2)
        diag[0] += g; rhs[0] += g * val
        gb.append(g)
    mat = coo_matrix((-np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    mat = mat + coo_matrix((diag.ravel(), (np.arange(n), np.arange(n))), shape=(n, n)).tocsr()
    u = spsolve(mat.tocsc(), rhs.ravel()).reshape(nz, nx)
    flows = [float((g * (u[0] - val)).sum()) for g, (_, val) in zip(gb, bottom)]
    return u, flows


# ---------------------------------------------------------------- layer stack in z
def z_structure(sensor: em.Sensor, cond: em.Conditions):
    """Edges, per-cell permeability D*K per species (nz, ns), enzyme mask and coating mask (matches em.build_grid)."""
    wd = em.water_d(cond.temp_c)
    layers = list(sensor.layers) + [em.Layer("boundary", cond.boundary_um, {s: cond.boundary_d_ratio for s in em.SPECIES}, cells=30)]
    h, perm, enz, coat = [], [], [], []
    for li, layer in enumerate(layers):
        t = np.linspace(0, 1, layer.cells + 1)
        w = np.diff(layer.thickness_um * 1e-6 * (0.5 - 0.5 * np.cos(np.pi * t)))
        h.extend(w)
        perm.extend([[wd[s] * layer.d_ratio[s] * layer.k(s) for s in em.SPECIES]] * layer.cells)
        enz.extend([layer.enzyme] * layer.cells)
        coat.extend([li < len(sensor.layers)] * layer.cells)
    h = np.array(h)
    return np.concatenate([[0], np.cumsum(h)]), np.array(perm), np.array(enz), np.array(coat), wd


def coated_problem(sensor, cond, x, axisym, coat_radius_m, species):
    """Per-cell permeability and peroxide source for a coating that covers |x| <= coat_radius_m."""
    z, perm_z, enz, coat, wd = z_structure(sensor, cond)
    m = em.Model(sensor, cond)
    y1 = m.steady()
    c1 = y1.reshape(len(em.SPECIES), m.n)
    rate = m.rate(c1)  # mol/m^3/s per 1D cell
    xc = (x[1:] + x[:-1]) / 2
    under = xc <= coat_radius_m
    s = em.SPECIES.index(species)
    liquid = np.array([wd[species] * cond.boundary_d_ratio])
    perm = np.where(coat[:, None] & ~under[None, :], liquid[0], perm_z[:, s][:, None] * np.ones_like(xc)[None, :])
    src = (rate * enz)[:, None] * under[None, :] if species == "peroxide" else np.zeros((len(rate), len(xc)))
    return z, perm, src, m, y1


def disk_current_nA(sensor, cond, species="peroxide", cells_r=80, coat_radius_mm=None, extent_mm=None, cells_per=60):
    """Axisymmetric current at the WE disk for peroxide (from enzyme) or acetaminophen (bulk), nA."""
    a = A0_RADIUS_M
    coat_r = (coat_radius_mm * 1e-3) if coat_radius_mm is not None else 1e9
    rmax = (extent_mm * 1e-3) if extent_mm is not None else 10 * a
    x = join(cosine_edges(0, a, cells_per // 2).__mul__(1.0)[:], one_sided_edges(a, rmax, cells_r))
    x = join(a * np.sin(np.pi / 2 * np.linspace(0, 1, cells_per // 2 + 1)), one_sided_edges(a, rmax, cells_r))
    z, perm, src, m, y1 = coated_problem(sensor, cond, x, True, coat_r, species)
    top = cond.acetaminophen_mM if species == "acetaminophen" else 0.0
    frac = (x[1:] <= a * (1 + 1e-9)).astype(float)
    u, (flow,) = solve_steady(x, z, perm, src, True, [(frac, 0.0)], top)
    # flow is the mol/s into the electrode for peroxide produced (sources) minus ... sign: sink positive
    return 2 * em.F * flow * 1e9, m, y1


def one_d_current_nA(m, y1, species):
    return m.current_nA(y1)[species]


# ---------------------------------------------------------------- 3D Laplace for IR
def laplace_3d(xe, ye, ze, kappa, electrodes, outer=(), sym=()):
    """Steady current in a conductor, no flux on all faces except Dirichlet electrodes.

    electrodes: list of (weight[ny, nx] area fraction on z=0, potential). outer: faces among
    'x+', 'y+', 'z+' held at 0 V (far field). Returns phi (nz, ny, nx) and current into each electrode (A).
    """
    nx, ny, nz = len(xe) - 1, len(ye) - 1, len(ze) - 1
    dx, dy, dz = np.diff(xe), np.diff(ye), np.diff(ze)
    shape = (nz, ny, nx)
    idx = np.arange(nz * ny * nx).reshape(shape)
    ax = dy[None, :, None] * dz[:, None, None]
    ay = dx[None, None, :] * dz[:, None, None]
    az = dx[None, None, :] * dy[None, :, None]
    diag = np.zeros(shape)
    rhs = np.zeros(shape)
    rows, cols, vals = [], [], []

    def link(sl_a, sl_b, g):
        rows.extend([idx[sl_a].ravel(), idx[sl_b].ravel()]); cols.extend([idx[sl_b].ravel(), idx[sl_a].ravel()])
        vals.extend([g.ravel(), g.ravel()])
        diag[sl_a] += g; diag[sl_b] += g

    sa = lambda i, j, k: (slice(*k), slice(*j), slice(*i))
    link(sa((0, nx - 1), (0, ny), (0, nz)), sa((1, nx), (0, ny), (0, nz)),
         kappa * ax[:, :, :nx - 1] / ((dx[:-1] + dx[1:]) / 2)[None, None, :])
    link(sa((0, nx), (0, ny - 1), (0, nz)), sa((0, nx), (1, ny), (0, nz)),
         kappa * ay[:, :ny - 1, :] / ((dy[:-1] + dy[1:]) / 2)[None, :, None])
    link(sa((0, nx), (0, ny), (0, nz - 1)), sa((0, nx), (0, ny), (1, nz)),
         kappa * az[:nz - 1] / ((dz[:-1] + dz[1:]) / 2)[:, None, None])
    if "x+" in outer:
        diag[:, :, -1] += kappa * ax[:, :, -1] / (dx[-1] / 2)
    if "y+" in outer:
        diag[:, -1, :] += kappa * ay[:, -1, :] / (dy[-1] / 2)
    if "z+" in outer:
        diag[-1] += kappa * az[-1] / (dz[-1] / 2)
    gs = []
    for w, v in electrodes:
        g = kappa * az[0] * w / (dz[0] / 2)
        diag[0] += g; rhs[0] += g * v
        gs.append(g)
    n = diag.size
    mat = (coo_matrix((-np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
           + coo_matrix((diag.ravel(), (np.arange(n), np.arange(n))), shape=(n, n)).tocsr())
    dinv = 1.0 / mat.diagonal()
    from scipy.sparse.linalg import LinearOperator
    phi, info = cg(mat, rhs.ravel(), rtol=1e-11, atol=0, maxiter=20000, M=LinearOperator(mat.shape, lambda v: dinv * v))
    if info != 0:
        raise RuntimeError(f"CG did not converge ({info})")
    phi = phi.reshape(shape)
    return phi, [float((g * (v - phi[0])).sum()) for g, (_, v) in zip(gs, electrodes)]


def disk_weights(xe, ye, cx, cy, radius, sub=6):
    """Area fraction of each z=0 face cell inside a disk (supersampled)."""
    f = np.zeros((len(ye) - 1, len(xe) - 1))
    s = (np.arange(sub) + 0.5) / sub
    for j in range(len(ye) - 1):
        yy = ye[j] + (ye[j + 1] - ye[j]) * s
        for i in range(len(xe) - 1):
            xx = xe[i] + (xe[i + 1] - xe[i]) * s
            f[j, i] = (((xx[None, :] - cx) ** 2 + (yy[:, None] - cy) ** 2) <= radius ** 2).mean()
    return f


def rect_weights(xe, ye, x0, x1, y0, y1):
    ox = np.clip(np.minimum(xe[1:], x1) - np.maximum(xe[:-1], x0), 0, None) / np.diff(xe)
    oy = np.clip(np.minimum(ye[1:], y1) - np.maximum(ye[:-1], y0), 0, None) / np.diff(ye)
    return oy[:, None] * ox[None, :]


def ir_drop(kappa=KAPPA_PBS, cell_m=2.0e-4, height_m=15e-3, margin_m=10e-3):
    """WE -> CE resistance and WE-to-RE uncompensated resistance for the A0 layout (3D)."""
    mm = 1e-3
    cx_w, cy = WE["x"] * mm, WE["y"] * mm
    r = A0_RADIUS_M
    hx = lambda e: ((e["x"] - e["width"] / 2) * mm, (e["x"] + e["width"] / 2) * mm)
    ce0, ce1 = hx(CE)
    re0, re1 = hx(RE)
    # half-space y >= y0 by mirror symmetry (all electrodes centred on y = 33 mm)
    xb = sorted({cx_w - margin_m, re0 - margin_m + 4e-3, re0, re1, ce0, ce1, cx_w - r, cx_w, cx_w + r, cx_w + margin_m})
    xe = segmented_edges(xb, cell_m * 2)
    yb = [cy, cy + r, cy + RE["height"] / 2 * mm, cy + CE["height"] / 2 * mm, cy + margin_m + 5e-3]
    ye = segmented_edges(yb, cell_m * 2)
    ze = one_sided_edges(0, height_m, 28)
    w_we = disk_weights(xe, ye, cx_w, cy, r)
    w_ce = rect_weights(xe, ye, ce0, ce1, cy, cy + CE["height"] / 2 * mm)
    w_re = rect_weights(xe, ye, re0, re1, cy, cy + RE["height"] / 2 * mm)
    phi, (i_we, i_ce) = laplace_3d(xe, ye, ze, kappa, [(w_we, 1.0), (w_ce, 0.0)])
    i_we *= 2  # mirrored half
    phi_re = float((phi[0] * w_re * np.outer(np.diff(ye), np.diff(xe))).sum() / (w_re * np.outer(np.diff(ye), np.diff(xe))).sum())
    jy = int(np.searchsorted(ye, cy + 1e-9)) % len(ye)  # first row = symmetry line y=cy
    line = [(float((xe[i] + xe[i + 1]) / 2 / mm), float(phi[0, 0, i])) for i in range(len(xe) - 1)]
    return {
        "kappa_S_per_m": kappa,
        "cells": int(phi.size),
        "R_we_ce_ohm": 1.0 / i_we,
        "R_uncompensated_we_re_ohm": (1.0 - phi_re) / i_we,
        "phi_re_fraction": phi_re,
        "R_disk_to_infinity_ohm": 1 / (4 * kappa * r),
        "profile_mm_phi": line,
    }


# ---------------------------------------------------------------- reports
def edge_error(sensor_name="gox_pu", cond=em.BEAKER, **kw):
    sensor = em.PRESETS[sensor_name]
    i2, m, y1 = disk_current_nA(sensor, cond, "peroxide", **kw)
    i1 = one_d_current_nA(m, y1, "peroxide")
    ap = replace(cond, glucose_mM=0.0, acetaminophen_mM=0.13)
    j2, m2, y2 = disk_current_nA(sensor, ap, "acetaminophen", **kw)
    j1 = one_d_current_nA(m2, y2, "acetaminophen")
    return {"glucose_1d_nA": i1, "glucose_2d_nA": i2, "glucose_error_pct": 100 * (i1 / i2 - 1),
            "apap_1d_nA": j1, "apap_2d_nA": j2, "apap_error_pct": 100 * (j1 / j2 - 1)}


def crosstalk_planar(sensor, cond, coat_margin_mm=0.3, cell_m=1e-4):
    """Planar x-z cross-section through RE, CE, WE: peroxide reaching CE (perfect sink) and RE."""
    mm = 1e-3
    xw0, xw1 = (WE["x"] - WE["diameter"] / 2) * mm, (WE["x"] + WE["diameter"] / 2) * mm
    c0, c1 = (CE["x"] - CE["width"] / 2) * mm, (CE["x"] + CE["width"] / 2) * mm
    r0, r1 = (RE["x"] - RE["width"] / 2) * mm, (RE["x"] + RE["width"] / 2) * mm
    cm = coat_margin_mm * mm
    breaks = sorted({0.0, r0, r1, c0, c1, xw0 - cm, xw0, xw1, xw1 + cm, 12e-3})
    x = segmented_edges(breaks, cell_m)
    z, perm, src, m, y1 = coated_problem(sensor, cond, x, False, 0.0, "peroxide")
    xc = (x[1:] + x[:-1]) / 2
    # coating mask: |x - x_we| <= r + margin; rebuild with a shifted centre
    z, perm_z, enz, coat, wd = z_structure(sensor, cond)
    under = (xc >= xw0 - cm) & (xc <= xw1 + cm)
    s = em.P
    perm = np.where(coat[:, None] & ~under[None, :], wd["peroxide"] * cond.boundary_d_ratio, perm_z[:, s][:, None] * np.ones_like(xc)[None, :])
    rate = m.rate(y1.reshape(len(em.SPECIES), m.n))
    src = (rate * enz)[:, None] * under[None, :]
    fw = ((xc >= xw0) & (xc <= xw1)).astype(float)
    fc = ((xc >= c0) & (xc <= c1)).astype(float)
    out = {}
    for label, bottom in (("with_CE_sink", [(fw, 0.0), (fc, 0.0)]), ("no_CE", [(fw, 0.0)])):
        u, flows = solve_steady(x, z, perm, src, False, bottom, 0.0)
        c_top = u[:, :]  # u == c for peroxide (K=1 outside coating)
        zi = int(np.searchsorted(z, sum(l.thickness_um for l in sensor.layers) * 1e-6 + 1e-12))  # first boundary cell
        sel = lambda a, b: (xc >= a) & (xc <= b)
        produced = float((src * np.diff(x)[None, :] * np.diff(z)[:, None]).sum())
        res = {"WE_collected_frac": flows[0] / produced,
               "c_at_membrane_surface_over_WE_uM": float(np.mean(u[zi, sel(xw0, xw1)]) * 1e3),
               "c_RE_surface_uM": float(np.mean(u[zi, sel(r0, r1)]) * 1e3),
               "c_CE_edge_surface_uM": float(u[zi, sel(c1, c1 + 3e-4)].mean() * 1e3)}
        if len(flows) > 1:
            res["CE_captured_frac"] = flows[1] / produced
        out[label] = res
    return out


def crosstalk_axisym(sensor, cond):
    """WE disk alone: peroxide concentration at the CE/RE radii (edges nearest the WE)."""
    a = A0_RADIUS_M
    x = join(a * np.sin(np.pi / 2 * np.linspace(0, 1, 31)), one_sided_edges(a, 12e-3, 120))
    z, perm, src, m, y1 = coated_problem(sensor, cond, x, True, a + 0.3e-3, "peroxide")
    frac = (x[1:] <= a * (1 + 1e-9)).astype(float)
    u, (flow,) = solve_steady(x, z, perm, src, True, [(frac, 0.0)], 0.0)
    zi = int(np.searchsorted(z, sum(l.thickness_um for l in sensor.layers) * 1e-6 + 1e-12))
    xc = (x[1:] + x[:-1]) / 2
    r_ce = (WE["x"] - (CE["x"] + CE["width"] / 2)) * 1e-3 + 0.0  # WE centre -> nearest CE edge
    r_re = (WE["x"] - (RE["x"] + RE["width"] / 2)) * 1e-3
    at = lambda r: float(np.interp(r, xc, u[zi]) * 1e3)
    return {"c_surface_WE_uM": at(a * 0.5), "c_at_CE_edge_uM": at(r_ce), "c_at_RE_edge_uM": at(r_re),
            "r_CE_edge_mm": r_ce * 1e3, "r_RE_edge_mm": r_re * 1e3}


def main():
    out = Path(__file__).parent / "out"
    out.mkdir(exist_ok=True)
    report = {"layout_mm": {"WE_centre_x": WE["x"], "WE_diameter": WE["diameter"], "CE_x": CE["x"], "RE_x": RE["x"],
                             "WE_to_CE_edge_gap": WE["x"] - WE["diameter"] / 2 - (CE["x"] + CE["width"] / 2),
                             "CE_to_RE_edge_gap": CE["x"] - CE["width"] / 2 - (RE["x"] + RE["width"] / 2)}}

    edge = {}
    for name in ("gox_pu", "gox_pu_tissue"):
        for cname, cond in (("beaker_stirred_50um", replace(em.BEAKER, glucose_mM=5.0)),
                            ("tissue_100um", replace(em.TISSUE, glucose_mM=5.0)),
                            ("beaker_quiescent_1000um", replace(em.BEAKER, glucose_mM=5.0, boundary_um=1000.0))):
            # Glucose/O2 are taken as laterally uniform, which fails once the stagnant layer exceeds the
            # disk radius, so the quiescent case is only meaningful for acetaminophen (bulk-supplied).
            edge[f"{name}/{cname}"] = {
                "coating_over_disk_only": edge_error(name, cond, coat_radius_mm=0.6),
                "coating_extends_0p5mm": edge_error(name, cond, coat_radius_mm=1.1),
                "coating_everywhere": edge_error(name, cond),
            }
            if "quiescent" in cname:
                for v in edge[f"{name}/{cname}"].values():
                    v["glucose_error_pct"] = None
                    v["note"] = "glucose not valid: lateral glucose supply ignored; acetaminophen only"
            e = edge[f"{name}/{cname}"]
            print(f"1D error {name:14s} {cname:24s} glucose current: "
                  + "  ".join(f"{k}={v['glucose_error_pct'] if v['glucose_error_pct'] is not None else float('nan'):+6.1f}%" for k, v in e.items())
                  + "  | APAP: " + "  ".join(f"{v['apap_error_pct']:+6.1f}%" for v in e.values()))
    report["one_d_error"] = edge

    xt = {}
    for cname, cond in (("beaker_stirred_50um", replace(em.BEAKER, glucose_mM=25.0)),
                        ("tissue_100um", replace(em.TISSUE, glucose_mM=25.0)),
                        ("quiescent_5000um", replace(em.BEAKER, glucose_mM=25.0, boundary_um=5000.0))):
        s = em.PRESETS["gox_pu"]
        xt[cname] = {"planar_upper_bound": crosstalk_planar(s, cond), "axisymmetric_WE_alone": crosstalk_axisym(s, cond)}
        p = xt[cname]["planar_upper_bound"]["with_CE_sink"]
        a_ = xt[cname]["axisymmetric_WE_alone"]
        print(f"crosstalk {cname:20s} planar: CE captures {100*p['CE_captured_frac']:.2e} % of H2O2 made, c_RE {p['c_RE_surface_uM']:.2e} uM"
              f" | axisym: c at WE {a_['c_surface_WE_uM']:.1f} uM, CE edge {a_['c_at_CE_edge_uM']:.2e} uM, RE edge {a_['c_at_RE_edge_uM']:.2e} uM")
    report["crosstalk"] = xt

    ir = ir_drop()
    prof = ir.pop("profile_mm_phi")
    sens = em.PRESETS["gox_pu"]
    i_nA = {g: em.calibration(sens, em.BEAKER, [g])[0] for g in (5.0, 25.0)}
    ir["current_nA"] = {"gox_pu_5mM": i_nA[5.0], "gox_pu_25mM": i_nA[25.0]}
    ir["drop_mV"] = {k: v * 1e-9 * ir["R_uncompensated_we_re_ohm"] * 1e3 for k, v in ir["current_nA"].items()}
    ir["coating_conductivity_for_1mV_S_per_m_at_25mM"] = (
        20e-6 / (1e-3 / (i_nA[25.0] * 1e-9) * math.pi * A0_RADIUS_M ** 2))
    report["ir_drop"] = ir
    print("IR:", json.dumps({k: v for k, v in ir.items()}, indent=1))
    (out / "geometry_2d.json").write_text(json.dumps(report, indent=2) + "\n")
    plot(report, prof, out / "geometry_2d.png")


def plot(report, prof, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    names = [n for n in report["one_d_error"] if "quiescent" not in n]
    for k, label in (("coating_over_disk_only", "coating over disk only"), ("coating_extends_0p5mm", "+0.5 mm margin"),
                     ("coating_everywhere", "coating everywhere")):
        ax[0].plot(range(len(names)), [report["one_d_error"][n][k]["glucose_error_pct"] for n in names], "o", label=label)
    ax[0].set_xticks(range(len(names)), [n.replace("/", "\n") for n in names], fontsize=6)
    ax[0].set(ylabel="1D error in glucose current (%)", title="1D vs axisymmetric 2D, 1.2 mm disk")
    ax[0].legend(fontsize=7); ax[0].grid(alpha=0.3)
    xs, ph = zip(*prof)
    ax[1].plot(xs, ph)
    for e, c in ((WE, "C0"), (CE, "C1"), (RE, "C2")):
        w = e.get("width", e.get("diameter"))
        ax[1].axvspan(e["x"] - w / 2, e["x"] + w / 2, color=c, alpha=0.2)
    ax[1].set(xlabel="x along y=33 mm (mm)", ylabel="potential / (V_WE - V_CE)", title="Solution potential on the substrate (WE | CE | RE)")
    ax[1].grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path, dpi=130)


if __name__ == "__main__":
    main()
