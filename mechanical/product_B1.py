"""Open CGM B1 product concept: a reusable sealed pod on a disposable adhesive base.

Every part is a superellipse-section loft of a 2D profile, so surfaces stay smooth
and meshes are watertight by construction. Sized around the OCK-P1 board
(hardware/ock_p1: 22 x 18 x 0.8 mm) and an 18 x 9 x 2 mm (~12 mAh) LiPo pouch over its analog
half. A concept for form and fit review, not a validated wearable. Units: mm.
"""
from __future__ import annotations

import json
import math
import struct
from pathlib import Path

import numpy as np

OUT = Path(__file__).parent / "product_B1"
SITE_ASSETS = Path(__file__).parents[1] / "docs" / "assets"

P = {
    "pod": {"a": 13.8, "b": 11.7, "n": 3.0, "height": 5.7, "crown": 0.3, "wall": 1.0,
            "floor": 1.0, "bottom_round": 0.5, "top_round": 2.0},
    "base": {"margin": 1.4, "floor": 0.8, "rim": 1.4, "clearance": 0.15},
    "patch": {"a": 23.0, "b": 19.5, "n": 2.2, "thickness": 0.4, "taper": 2.5},
    "filament": {"diameter": 0.35, "length": 6.0},
    # OCK-P1 board and cell (board outline from hardware/ock_p1/build_board.py; the cell
    # sits over the analog half, clear of the ISP1807 antenna keep-out).
    "stack": {"board": [22.0, 18.0, 3.0], "board_thickness": 0.8, "component_height": 0.6,
              "module_height": 1.0, "tape": 0.1, "cell": [18.0, 9.0, 2.0], "cell_y": -4.0, "gap": 0.2},
}
SECTION_POINTS = 160


def arc(cx, cz, r, a0, a1, steps=12):
    t = np.linspace(math.radians(a0), math.radians(a1), steps)
    return [(cx + r * math.cos(v), cz + r * math.sin(v)) for v in t]


def superellipse(n, m=SECTION_POINTS):
    t = np.linspace(0, 2 * np.pi, m, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    return np.sign(c) * np.abs(c) ** (2 / n), np.sign(s) * np.abs(s) ** (2 / n)


def loft(profile, a, b, n):
    """Sweep a (r, z) profile, r measured on the major axis, around a superellipse.
    Profile must start and end on the axis (r == 0)."""
    ux, uy = superellipse(n)
    m = len(ux)
    prof = np.asarray(profile, dtype=float)
    prof[np.abs(prof[:, 0]) < 1e-9, 0] = 0.0
    assert prof[0, 0] == 0 and prof[-1, 0] == 0
    rings = []
    for r, z in prof[1:-1]:
        k = r / a
        rings.append(np.column_stack([a * k * ux, b * k * uy, np.full(m, z)]))
    top, bot = np.array([0, 0, prof[0, 1]]), np.array([0, 0, prof[-1, 1]])
    tris = []
    first = rings[0]
    for i in range(m):
        tris.append([top, first[i], first[(i + 1) % m]])
    for r0, r1 in zip(rings[:-1], rings[1:]):
        for i in range(m):
            j = (i + 1) % m
            tris.append([r0[i], r1[i], r1[j]])
            tris.append([r0[i], r1[j], r0[j]])
    last = rings[-1]
    for i in range(m):
        tris.append([bot, last[(i + 1) % m], last[i]])
    tris = np.array(tris)
    if signed_volume(tris) < 0:
        tris = tris[:, ::-1]
    return tris


def signed_volume(tris):
    return float(np.einsum("ij,ij->i", tris[:, 0], np.cross(tris[:, 1], tris[:, 2])).sum() / 6)


def validate(tris):
    key = lambda p: tuple(np.round(p, 5))
    directed = {}
    for t in tris:
        for u, v in ((0, 1), (1, 2), (2, 0)):
            e = (key(t[u]), key(t[v]))
            directed[e] = directed.get(e, 0) + 1
    undirected = {}
    for (u, v), c in directed.items():
        k = tuple(sorted((u, v)))
        undirected[k] = undirected.get(k, 0) + c
    return {
        "triangles": int(len(tris)),
        "nonmanifold_edges": sum(1 for c in undirected.values() if c != 2),
        "winding_errors": sum(1 for (u, v), c in directed.items() if c != 1 or directed.get((v, u), 0) != 1),
        "volume_mm3": round(signed_volume(tris), 2),
        "bounds_mm": [np.round(tris.reshape(-1, 3).min(0), 3).tolist(), np.round(tris.reshape(-1, 3).max(0), 3).tolist()],
    }


def write_stl(path: Path, tris, label: str):
    tris = tris.astype(np.float32)
    with path.open("wb") as f:
        f.write((f"Open CGM B1 {label}; mm; concept, not a medical device".encode() + b" " * 80)[:80])
        f.write(struct.pack("<I", len(tris)))
        for t in tris:
            nrm = np.cross(t[1] - t[0], t[2] - t[0])
            nrm = nrm / (np.linalg.norm(nrm) or 1)
            f.write(struct.pack("<12fH", *nrm, *t.ravel(), 0))


def pod_profiles():
    p = P["pod"]
    a, h, w, fl, rb, rt, cr = p["a"], p["height"], p["wall"], p["floor"], p["bottom_round"], p["top_round"], p["crown"]
    dome_r = a - rt
    dome = [(dome_r * (1 - s), h + cr * (1 - (1 - s) ** 2)) for s in np.linspace(1, 0, 14)]
    shell = dome + arc(a - rt, h - rt, rt, 90, 0, 16)[1:] + [
        (a, fl), (a - w, fl), (a - w, h - rt)] + arc(a - rt, h - rt, rt - w, 0, 90, 14)[1:] + [(0.0, h - w)]
    floor = [(0.0, fl), (a, fl)] + arc(a - rb, rb, rb, 0, -90, 10)[1:] + [(0.0, 0.0)]
    return shell, floor


def base_profile():
    p, pod = P["base"], P["pod"]
    a_in = pod["a"] + p["clearance"]
    a_out = pod["a"] + p["margin"]
    top = p["floor"] + p["rim"]
    lip = (a_out - a_in) / 2
    return ([(0.0, p["floor"]), (a_in, p["floor"]), (a_in, top - lip)]
            + arc(a_in + lip, top - lip, lip, 180, 0, 12)[1:]
            + [(a_out + 0.4, 0.5)] + arc(a_out, 0.4, 0.4, 15, -90, 8)[1:] + [(0.0, 0.0)])


def patch_profile():
    p = P["patch"]
    return [(0.0, p["thickness"]), (p["a"] - p["taper"], p["thickness"]), (p["a"], 0.05), (p["a"], 0.0), (0.0, 0.0)]


def filament():
    f = P["filament"]
    r = f["diameter"] / 2
    prof = [(0.0, 0.0), (r, 0.0), (r, -f["length"] + r)] + arc(0, -f["length"] + r, r, 0, -90, 6)[1:]
    return loft(prof, r, r, 2.0)


def _inside(points, a, b, n):
    return bool(np.all((np.abs(points[:, 0]) / a) ** n + (np.abs(points[:, 1]) / b) ** n <= 1))


def _rounded_rect(w, h, r, cx=0.0, cy=0.0, m=24):
    pts = []
    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        for t in np.linspace(0, np.pi / 2, m):
            pts.append((cx + sx * (w / 2 - r + r * math.cos(t)), cy + sy * (h / 2 - r + r * math.sin(t))))
    return np.array(pts)


def fit_check():
    """Board and cell outlines against the pod interior at the heights they occupy."""
    pod, s = P["pod"], P["stack"]
    a_i, b_i = pod["a"] - pod["wall"], (pod["a"] - pod["wall"]) * pod["b"] / pod["a"]
    ceiling = pod["height"] - pod["wall"]
    above_board = max(s["module_height"], s["component_height"] + s["tape"] + s["cell"][2])
    needed = s["board_thickness"] + above_board + s["gap"]
    rt_i = pod["top_round"] - pod["wall"]

    def section(z):  # interior semi-axes at height z, shrunk by the inner top fillet
        dz = max(0.0, z - (pod["height"] - pod["top_round"]))
        inset = rt_i - math.sqrt(max(rt_i**2 - dz**2, 0))
        return a_i - inset, (a_i - inset) * pod["b"] / pod["a"]

    w, h, r = s["board"]
    board = _rounded_rect(w + 0.6, h + 0.6, r + 0.3)
    z_board_top = pod["floor"] + s["board_thickness"]
    cw, ch, ct = s["cell"]
    cell = _rounded_rect(cw, ch, 0.5, cy=s["cell_y"])
    z_cell_top = z_board_top + s["component_height"] + s["tape"] + ct
    return {
        "interior_height_mm": round(ceiling - pod["floor"], 2),
        "stack_height_needed_mm": round(needed, 2),
        "height_ok": ceiling - pod["floor"] >= needed,
        "board_fits": _inside(board, *section(z_board_top), pod["n"]),
        "cell_fits": _inside(cell, *section(z_cell_top), pod["n"]),
        "pod_mm": [2 * pod["a"], 2 * pod["b"], round(pod["height"] + pod["crown"], 2)],
        "on_skin_height_mm": round(P["patch"]["thickness"] + P["base"]["floor"] + pod["height"] + pod["crown"], 2),
    }


def build():
    pod, base = P["pod"], P["base"]
    shell_prof, floor_prof = pod_profiles()
    b_ratio = pod["b"] / pod["a"]
    base_a = pod["a"] + base["margin"]
    parts = {
        "pod_shell": (loft(shell_prof, pod["a"], pod["b"], pod["n"]), "reusable pod shell"),
        "pod_floor": (loft(floor_prof, pod["a"], pod["b"], pod["n"]), "reusable pod floor"),
        "base": (loft(base_profile(), base_a, base_a * b_ratio, pod["n"]), "disposable base"),
        "patch": (loft(patch_profile(), P["patch"]["a"], P["patch"]["b"], P["patch"]["n"]), "adhesive patch"),
        "filament": (filament(), "sensor filament (illustrative)"),
    }
    # Assembly positions (z offsets) for viewers.
    z = {"patch": 0.0, "base": P["patch"]["thickness"], "filament": 0.0}
    z["pod_floor"] = z["base"] + base["floor"]
    z["pod_shell"] = z["pod_floor"]
    return parts, z


def render(parts, z, path: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgb
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    colors = {"patch": "#f2efe9", "base": "#c9ccd1", "pod_floor": "#2b2f36", "pod_shell": "#e7e3dc", "filament": "#b08d57"}
    fig = plt.figure(figsize=(9, 6.5), dpi=160)
    ax = fig.add_subplot(projection="3d")
    # One collection so matplotlib depth-sorts faces across parts.
    all_tris, all_colors = [], []
    light = np.array([-0.4, -0.5, 0.77])
    for name in ("filament", "patch", "base", "pod_floor", "pod_shell"):
        tris = parts[name][0] + np.array([0, 0, z[name]])
        normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-12
        shade = 0.5 + 0.5 * np.clip(normals @ light, 0, 1)
        all_tris.append(tris)
        all_colors.append(np.clip(np.array(to_rgb(colors[name])) * shade[:, None], 0, 1))
    ax.add_collection3d(Poly3DCollection(np.concatenate(all_tris), facecolors=np.concatenate(all_colors), linewidths=0))
    ax.set(xlim=(-28, 28), ylim=(-28, 28), zlim=(-14, 20))
    ax.set_box_aspect((1, 1, 34 / 56))
    ax.view_init(elev=24, azim=-58)
    ax.set_axis_off()
    fig.patch.set_alpha(0)
    fig.savefig(path, transparent=True, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def patch_svg(path: Path):
    p = P["patch"]
    ux, uy = superellipse(p["n"], 240)
    pts = " ".join(f"{p['a'] * x + p['a']:.3f},{p['b'] * y + p['b']:.3f}" for x, y in zip(ux, uy))
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{2 * p["a"]}mm" height="{2 * p["b"]}mm" '
        f'viewBox="0 0 {2 * p["a"]} {2 * p["b"]}"><polygon points="{pts}" fill="none" stroke="black" '
        f'stroke-width="0.1"/></svg>\n')


def main():
    OUT.mkdir(exist_ok=True)
    SITE_ASSETS.mkdir(parents=True, exist_ok=True)
    parts, z = build()
    report = {"revision": "B1", "units": "mm", "status": "product concept; no physical fit or material testing",
              "parameters": P, "assembly_z_mm": z, "fit": fit_check(), "meshes": {}}
    for name, (tris, label) in parts.items():
        report["meshes"][name] = validate(tris)
        write_stl(OUT / f"{name}.stl", tris, label)
        write_stl(SITE_ASSETS / f"{name}.stl", tris, label)
    patch_svg(OUT / "patch_diecut.svg")
    render(parts, z, OUT / "render.png")
    (OUT / "product_B1.json").write_text(json.dumps(report, indent=2, default=bool) + "\n")
    bad = {k: v for k, v in report["meshes"].items() if v["nonmanifold_edges"] or v["winding_errors"] or v["volume_mm3"] <= 0}
    print(json.dumps({"fit": report["fit"], "meshes": {k: (v["triangles"], v["volume_mm3"]) for k, v in report["meshes"].items()}}, indent=1, default=bool))
    if bad:
        raise SystemExit(f"invalid meshes: {list(bad)}")


if __name__ == "__main__":
    main()
