"""Generate the OCK-P1 pod board (KiCad 10, run with KiCad's bundled Python).

OCK-P1 is a glucose-only derivative of Biocoin v1.3: the same AD5940 analog
front end and decoupling (copied ball-for-ball from the pinned Biocoin layout),
the same nRF52840 port pins (so Biocoin firmware runs unchanged), an 8 x 8 mm
ISP1807 SiP instead of the 10 x 15.5 x 2.2 mm MDBT50Q module, a 3.0 V LDO and
bq25100 charger instead of the buck-boost, and no iontophoresis, mux, pH or
strain circuitry.

  python build_board.py <imported_biocoin.kicad_pcb> <out_dir> <kicad_footprints_dir>

The netlist below is the design source of truth (there is no schematic yet).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
LIB = HERE / "ock_p1.pretty"
STOCK = None  # KiCad stock footprint directory, argv[3]

MM = pcbnew.FromMM
W, H, R = 22.0, 18.0, 3.0           # board outline, mm, origin at centre, +y toward antenna edge
ANT_DEPTH = 4.3                     # ISP1807 keep-out: antenna half of the module to the board edge
EDGE_GAP = 0.3                      # module to board edge (copper-to-edge rule)
MODULE_AT = (0.0, H / 2 - 4.0 - EDGE_GAP)  # module centre = start of its antenna half

# ---------------------------------------------------------------- footprints

def isp1807_pads():
    """(number, x, y, w, h) in mm from the module's top-left corner, top view.
    Positions from the ISP1807 R19 dimension drawing (section 4.1), pad sizes
    from its SMT guideline (0.4 x 0.4 standard, 0.8 x 0.8 corners)."""
    pads = []
    c, s = 0.5125, 0.4
    big = 0.8
    xs9 = [1.40 + 0.65 * i for i in range(9)]
    xs8 = [1.725 + 0.65 * i for i in range(8)]
    rows = [
        (0.325, list(zip([48, 46, 44, 42, 40, 38, 36, 34, 32], xs9))),
        (0.95, list(zip([47, 45, 43, 41, 39, 37, 35, 33], xs8))),
        (1.725, [(3, 0.95)] + list(zip([56, 55, 54, 53, 52, 51, 50, 49], xs8)) + [(29, 7.05)]),
        (2.375, [(5, 0.95)] + list(zip([64, 63, 62, 61, 60, 59, 58, 57], xs8)) + [(27, 7.05)]),
        (3.15, list(zip([9, 11, 13, 15, 17, 19, 21, 23], xs8))),
        (3.8, list(zip([8, 10, 12, 14, 16, 18, 20, 22, 24], xs9))),
        (7.675, list(zip([69, 70, 71, 72, 73, 74], [1.5, 2.5, 3.5, 4.5, 5.5, 6.5]))),
    ]
    for y, items in rows:
        for n, x in items:
            pads.append((n, x, y, s, s))
    for n, y in ((2, 1.40), (4, 2.05), (6, 2.70), (65, 4.55), (66, 5.55), (67, 6.55)):
        pads.append((n, 0.3125, y, s, s))
    for n, y in ((30, 1.40), (28, 2.05), (26, 2.70), (78, 4.55), (77, 5.55), (76, 6.55)):
        pads.append((n, 7.6875, y, s, s))
    for n, x, y in ((1, c, c), (31, 8 - c, c), (7, c, 3.6), (25, 8 - c, 3.6), (68, c, 8 - c), (75, 8 - c, 8 - c)):
        pads.append((n, x, y, big, big))
    assert sorted(p[0] for p in pads) == list(range(1, 79)), "ISP1807 pad set incomplete"
    return pads


def make_isp1807():
    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPID(pcbnew.LIB_ID("ock_p1", "InsightSiP_ISP1807_LGA-78_8x8mm"))
    fp.SetReference("M1")
    fp.SetValue("ISP1807-LR")
    for n, x, y, w, h in isp1807_pads():
        pad = pcbnew.PAD(fp)
        pad.SetNumber(str(n))
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pad.SetShape(pcbnew.PAD_SHAPE_RECT)
        pad.SetSize(pcbnew.VECTOR2I(MM(w), MM(h)))
        pad.SetPosition(pcbnew.VECTOR2I(MM(x - 4), MM(y - 4)))
        pad.SetLayerSet(pad.SMDMask())
        fp.Add(pad)
    for layer, inset in ((pcbnew.F_SilkS, -0.1), (pcbnew.F_CrtYd, -0.25), (pcbnew.F_Fab, 0.0)):
        rect = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_RECT)
        rect.SetStart(pcbnew.VECTOR2I(MM(-4 + inset), MM(-4 + inset)))
        rect.SetEnd(pcbnew.VECTOR2I(MM(4 - inset), MM(4 - inset)))
        rect.SetLayer(layer)
        rect.SetWidth(MM(0.05 if layer != pcbnew.F_SilkS else 0.1))
        fp.Add(rect)
    return fp


def extract_from_biocoin(src: pcbnew.BOARD):
    """Copy the proven footprints out of the imported Biocoin layout."""
    names = {}
    for ref in ("U1", "Q1", "U8", "L4"):
        f = next(x for x in src.GetFootprints() if x.GetReference() == ref)
        fp = pcbnew.FOOTPRINT(f)
        if fp.IsFlipped():
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        fp.SetOrientationDegrees(0)
        fp.SetPosition(pcbnew.VECTOR2I(0, 0))
        name = str(fp.GetFPID().GetLibItemName())
        fp.SetFPID(pcbnew.LIB_ID("ock_p1", name))
        names[ref] = name
        save_fp(fp, name)
    return names


def save_fp(fp, name):
    io = pcbnew.PCB_IO_KICAD_SEXPR()
    if not LIB.exists():
        io.CreateLibrary(str(LIB))
    io.FootprintSave(str(LIB), fp)


def load(lib: str, name: str):
    path = LIB if lib == "ock_p1" else STOCK / f"{lib}.pretty"
    fp = pcbnew.FootprintLoad(str(path), name)
    if fp is None:
        raise SystemExit(f"footprint not found: {lib}:{name}")
    return fp


def contact_pad(name, dia=1.6, side="B"):
    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPID(pcbnew.LIB_ID("ock_p1", f"ContactPad_D{dia}mm"))
    pad = pcbnew.PAD(fp)
    pad.SetNumber("1")
    pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(pcbnew.VECTOR2I(MM(dia), MM(dia)))
    pad.SetLayerSet(pad.SMDMask())
    fp.Add(pad)
    return fp


def battery_tab():
    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPID(pcbnew.LIB_ID("ock_p1", "BatteryTab_1.2x2.0mm"))
    pad = pcbnew.PAD(fp)
    pad.SetNumber("1")
    pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    pad.SetShape(pcbnew.PAD_SHAPE_RECT)
    pad.SetSize(pcbnew.VECTOR2I(MM(1.2), MM(2.0)))
    pad.SetLayerSet(pad.SMDMask())
    fp.Add(pad)
    return fp


# ---------------------------------------------------------------- netlist

C0201 = ("Capacitor_SMD", "C_0201_0603Metric")
C0402 = ("Capacitor_SMD", "C_0402_1005Metric")
R0201 = ("Resistor_SMD", "R_0201_0603Metric")
LED0402 = ("LED_SMD", "LED_0402_1005Metric")
DSBGA6 = ("Package_BGA", "Texas_DSBGA-6_0.9x1.4mm_Layout2x3_P0.5mm")

AD5940_NETS = {
    "A4": "AFE_AVDD", "F2": "AFE_AVDD", "A5": "VREF_1V8", "A6": "WE", "A7": "CE", "A8": "RE",
    "B1": "RCAL1", "C1": "RCAL0", "B4": "LPF0", "B7": "VZERO0", "B8": "RC0_1", "C8": "RC0_0",
    "C7": "VBIAS0", "D1": "VBIAS_CAP", "D7": "VREF_2V5", "D8": "AVDD_REG",
    "C4": "GND", "D5": "GND", "E3": "GND", "E4": "GND", "E5": "GND", "E6": "GND",
    "E7": "SPI_MOSI", "E8": "SPI_MISO", "F1": "AFE_RESET", "F3": "AFE_VDD", "G2": "AFE_VDD",
    "G3": "DVDD_REG_1V8", "F5": "AFE_INT", "F7": "SPI_CS", "F8": "SPI_SCK",
}

ISP1807_NETS = {
    **{str(n): "GND" for n in (1, 7, 14, 16, 18, 21, 23, 24, 25, 31)},
    "26": "VDD", "12": "VBUS", "28": "SWDIO", "30": "SWDCLK", "20": "ANT", "22": "ANT",
    # Same nRF52840 port pins as Biocoin v1.3 (HWConfig/pins.h + variant.cpp).
    "29": "SPI_MOSI",       # P0.13
    "37": "SPI_MISO",       # P0.15
    "5": "SPI_SCK",         # P0.14
    "35": "SPI_CS",         # P0.04  PIN_SPI_CS (D14)
    "36": "AFE_INT",        # P0.05  PIN_AFE_IntPin_GPIO0 (D15)
    "40": "AFE_RESET",      # P0.02  PIN_AFE_RESET (D18)
    "6": "AFE_VDD_CTRL",    # P0.26  PIN_AFE_VDD_CTRL (D9), active low
    "46": "VDIV",           # P0.29  PIN_VDIV (D20, AIN5)
    "15": "LED",            # P0.20  PIN_LED (D28)
}

# ref: (footprint, value, {pad: net}, (x, y, rot_deg, side))
# U1 balls: x = UX - 1.4 + 0.4 (col - 1), y = UY - 1.2 + 0.4 (row - A). Row A (WE/CE/RE, AVDD,
# VREF_1V8) faces the top edge, column 1 (RCAL, VBIAS_CAP, RESET) the left, column 8
# (RC0_x, AVDD_REG, MISO, SCLK) the right, row G (IOVDD, DVDD_REG) the module.
UX, UY = -5.6, -4.4
PARTS = {
    "U1": (("ock_p1", "@U1"), "AD5940BCBZ", AD5940_NETS, (UX, UY, 0, "F")),
    "M1": (("ock_p1", "@M1"), "ISP1807-LR", ISP1807_NETS, (*MODULE_AT, 0, "F")),
    "U2": (("Package_SON", "Texas_X2SON-4_1x1mm_P0.65mm"), "TPS7A0230PDQNR", {"1": "VDD", "2": "GND", "3": "VBAT", "4": "VBAT", "5": "GND"}, (8.4, -6.8, 0, "F")),
    "Q1": (("ock_p1", "@Q1"), "CSD75208W1015", {"B1": "VDD", "B2": "VDD", "C1": "AFE_VDD_CTRL", "C2": "AFE_VDD", "A2": "VDD"}, (1.6, -6.8, 0, "F")),
    "U3": (DSBGA6, "BQ25100YFPR", {"A1": "VBAT", "A2": "VBUS", "B1": "TS", "B2": "ISET", "C1": "PRETERM", "C2": "GND"}, (6.4, -3.2, 0, "F")),
    "U4": (("ock_p1", "@U8"), "MAX44264EWT+T", {"A1": "VDIV_RAW", "A2": "GND", "B1": "VDIV", "C1": "VDIV", "B2": "VDD"}, (3.0, -1.4, 0, "F")),
    "FB1": (("ock_p1", "@L4"), "MMZ0603S601HT000", {"1": "AFE_VDD", "2": "AFE_AVDD"}, (-1.6, -7.8, 0, "F")),
    # AD5940 support network, values from Biocoin v1.3 schematic page 1.
    "C3": (C0201, "4.7uF", {"1": "VREF_1V8", "2": "GND"}, (UX - 0.6, UY - 2.4, 90, "F")),      # A5
    "C10": (C0201, "4.7uF", {"1": "AFE_AVDD", "2": "GND"}, (UX - 1.4, UY - 2.4, 90, "F")),    # A4
    "C11": (C0201, "100nF", {"1": "AFE_AVDD", "2": "GND"}, (UX - 2.2, UY - 2.4, 90, "F")),
    "C12": (C0201, "100nF", {"1": "AFE_AVDD", "2": "GND"}, (UX - 3.0, UY - 2.4, 90, "F")),
    "R1": (R0201, "10k 0.1%", {"1": "RCAL1", "2": "RCAL0"}, (UX - 2.6, UY - 0.6, 90, "F")),   # B1/C1
    "C4": (C0201, "470nF", {"1": "VBIAS_CAP", "2": "GND"}, (UX - 2.6, UY + 0.8, 90, "F")),   # D1
    "C8": (C0402, "33nF", {"1": "RC0_0", "2": "RC0_1"}, (UX + 2.6, UY - 0.6, 90, "F")),       # B8/C8
    "C5": (C0201, "470nF", {"1": "AVDD_REG", "2": "GND"}, (UX + 2.6, UY + 1.4, 90, "F")),     # D8
    "C6": (C0402, "100nF", {"1": "VZERO0", "2": "GND"}, (UX + 3.6, UY - 0.6, 90, "F")),       # B7 (via)
    "C7": (C0402, "100nF", {"1": "VBIAS0", "2": "GND"}, (UX + 3.6, UY + 1.4, 90, "F")),       # C7 (via)
    "C2": (C0201, "470nF", {"1": "VREF_2V5", "2": "GND"}, (UX + 0.6, UY - 2.4, 90, "F")),     # D7 (via)
    "C9": (C0201, "1uF", {"1": "LPF0", "2": "GND"}, (UX + 1.4, UY - 2.4, 90, "F")),  # B4 (via); Biocoin value unrecorded
    "C13": (C0201, "4.7uF", {"1": "AFE_VDD", "2": "GND"}, (UX - 1.2, UY + 2.4, 90, "F")),     # G2
    "C14": (C0201, "100nF", {"1": "AFE_VDD", "2": "GND"}, (UX - 2.0, UY + 2.4, 90, "F")),
    "C1": (C0201, "470nF", {"1": "DVDD_REG_1V8", "2": "GND"}, (UX - 0.4, UY + 2.4, 90, "F")),  # G3
    # Power
    "C15": (C0402, "4.7uF", {"1": "VBAT", "2": "GND"}, (9.9, -6.8, 90, "F")),
    "C16": (C0402, "4.7uF", {"1": "VDD", "2": "GND"}, (6.9, -6.8, 90, "F")),
    "C17": (C0402, "1uF", {"1": "VBUS", "2": "GND"}, (6.4, -0.8, 0, "F")),
    "R2": (R0201, "9.09k", {"1": "ISET", "2": "GND"}, (8.6, -3.2, 90, "F")),      # 15 mA fast charge
    "R3": (R0201, "6.04k", {"1": "PRETERM", "2": "GND"}, (4.0, -2.6, 0, "F")),    # Ichg/10 term
    "R4": (R0201, "10k", {"1": "TS", "2": "GND"}, (4.0, -3.8, 0, "F")),           # no NTC
    "R5": (R0201, "10M", {"1": "AFE_VDD_CTRL", "2": "VDD"}, (1.6, -5.2, 0, "F")), # AFE off at reset
    "R6": (R0201, "10M", {"1": "VBAT", "2": "VDIV_RAW"}, (1.8, -2.6, 90, "F")),
    "R7": (R0201, "4.99M", {"1": "VDIV_RAW", "2": "GND"}, (1.8, -1.2, 90, "F")),
    "C18": (C0201, "4.7uF", {"1": "VDD", "2": "GND"}, (5.0, 2.6, 90, "F")),
    "C19": (C0201, "100nF", {"1": "VDD", "2": "GND"}, (5.8, 2.6, 90, "F")),
    "D1": (LED0402, "APHHS1005LCGCK", {"1": "GND", "2": "LED_A"}, (-1.4, -0.4, 0, "F")),
    "R8": (R0201, "5.1k", {"1": "LED", "2": "LED_A"}, (-1.4, -1.4, 0, "F")),
    # Battery tabs (top) and spring-contact pads (bottom, ENIG)
    "BT1": ("tab", "VBAT", {"1": "VBAT"}, (9.8, -3.6, 0, "F")),
    "BT2": ("tab", "GND", {"1": "GND"}, (9.8, -0.8, 0, "F")),
    "TP1": ("contact", "WE", {"1": "WE"}, (-9.4, -1.2, 0, "B")),
    "TP2": ("contact", "RE", {"1": "RE"}, (-9.4, -6.8, 0, "B")),
    "TP3": ("contact", "CE", {"1": "CE"}, (-9.4, -4.0, 0, "B")),
    "TP4": ("contact", "VBUS", {"1": "VBUS"}, (3.0, -7.4, 0, "B")),
    "TP5": ("contact", "GND", {"1": "GND"}, (5.6, -7.4, 0, "B")),
    "TP6": ("contact", "SWDIO", {"1": "SWDIO"}, (3.0, -4.8, 0, "B")),
    "TP7": ("contact", "SWDCLK", {"1": "SWDCLK"}, (5.6, -4.8, 0, "B")),
}

# Inner WLCSP/LGA pads get a capped via-in-pad (POFV) so the router can escape them.
VIA_IN_PAD = {
    "U1": ["B4", "B7", "C4", "C7", "D5", "D7", "E3", "E4", "E5", "E6", "E7", "F2", "F3", "F5", "F7"],
    "M1": ["37", "35", "15", "21", "23", "14", "16", "18", "24", "12"],
}


# ---------------------------------------------------------------- board

def outline(board):
    hw, hh = W / 2, H / 2
    pts = [(-hw + R, -hh), (hw - R, -hh), (hw, -hh + R), (hw, hh - R), (hw - R, hh), (-hw + R, hh), (-hw, hh - R), (-hw, -hh + R)]
    for i in range(0, 8, 2):
        a, b = pts[i], pts[i + 1]
        seg = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1])))
        seg.SetEnd(pcbnew.VECTOR2I(MM(b[0]), MM(b[1])))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(MM(0.05))
        board.Add(seg)
    for cx, cy, start in ((hw - R, -hh + R, (hw - R, -hh)), (hw - R, hh - R, (hw, hh - R)),
                          (-hw + R, hh - R, (-hw + R, hh)), (-hw + R, -hh + R, (-hw, -hh + R))):
        arc = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        arc.SetCenter(pcbnew.VECTOR2I(MM(cx), MM(cy)))
        arc.SetStart(pcbnew.VECTOR2I(MM(start[0]), MM(start[1])))
        arc.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T), True)
        arc.SetLayer(pcbnew.Edge_Cuts)
        arc.SetWidth(MM(0.05))
        board.Add(arc)


def rect_zone(board, x0, y0, x1, y1, layers, net=None, rule_area=False, name=""):
    z = pcbnew.ZONE(board)
    ls = pcbnew.LSET()
    for l in layers:
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    poly = z.Outline()
    poly.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        poly.Append(MM(x), MM(y))
    if rule_area:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
    else:
        z.SetNet(net)
        z.SetMinThickness(MM(0.1))
        z.SetLocalClearance(MM(0.1))
        z.SetThermalReliefGap(MM(0.12))
        z.SetThermalReliefSpokeWidth(MM(0.12))
    z.SetZoneName(name)
    board.Add(z)
    return z


def copper_layers():
    return [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu]


def build(src_path: str, out_dir: Path):
    global STOCK
    STOCK = Path(sys.argv[3])
    src = pcbnew.LoadBoard(src_path)
    bio = extract_from_biocoin(src)
    save_fp(make_isp1807(), "InsightSiP_ISP1807_LGA-78_8x8mm")
    save_fp(contact_pad("TP"), "ContactPad_D1.6mm")
    save_fp(battery_tab(), "BatteryTab_1.2x2.0mm")

    board = pcbnew.BOARD()
    board.SetCopperLayerCount(6)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(MM(0.8))
    ds.m_TrackMinWidth = MM(0.09)
    ds.m_MinClearance = MM(0.09)
    ds.m_ViasMinSize = MM(0.25)
    ds.m_MinThroughDrill = MM(0.15)
    ds.m_ViasMinAnnularWidth = MM(0.05)
    ds.m_HoleToHoleMin = MM(0.2)
    ds.m_CopperEdgeClearance = MM(0.2)
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetTrackWidth(MM(0.09))
    nc.SetClearance(MM(0.09))
    nc.SetViaDiameter(MM(0.25))
    nc.SetViaDrill(MM(0.15))
    outline(board)

    nets = {}

    def net(name):
        if name not in nets:
            ni = pcbnew.NETINFO_ITEM(board, name)
            board.Add(ni)
            nets[name] = ni
        return nets[name]

    for ref, (fpid, value, padnets, (x, y, rot, side)) in PARTS.items():
        if fpid == "tab":
            fp = load("ock_p1", "BatteryTab_1.2x2.0mm")
        elif fpid == "contact":
            fp = load("ock_p1", "ContactPad_D1.6mm")
        elif fpid[1].startswith("@"):
            src_ref = fpid[1][1:]
            fp = load("ock_p1", bio[src_ref] if src_ref in bio else "InsightSiP_ISP1807_LGA-78_8x8mm")
        else:
            fp = load(*fpid)
        fp.SetReference(ref)
        fp.SetValue(value)
        board.Add(fp)
        fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        fp.SetOrientationDegrees(rot)
        if side == "B":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        known = {p.GetNumber() for p in fp.Pads()}
        missing = set(padnets) - known
        if missing:
            raise SystemExit(f"{ref}: pads {sorted(missing)} not in footprint {sorted(known)}")
        for pad in fp.Pads():
            n = padnets.get(pad.GetNumber())
            if n:
                pad.SetNet(net(n))

    # Via-in-pad for inner pads, on the pad centre.
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    for ref, padnums in VIA_IN_PAD.items():
        for pad in fps[ref].Pads():
            if pad.GetNumber() in padnums and pad.GetNetCode() > 0:
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pad.GetPosition())
                v.SetWidth(MM(0.25))
                v.SetDrill(MM(0.15))
                v.SetNet(pad.GetNet())
                board.Add(v)

    # ISP1807 antenna keep-out: full board width, ANT_DEPTH from the antenna edge, all copper layers.
    rect_zone(board, -W / 2 - 0.5, H / 2 - ANT_DEPTH, W / 2 + 0.5, H / 2 + 0.5, copper_layers(), rule_area=True,
              name="ANTENNA_KEEPOUT")
    # Ground planes on In1 and In4; In2/In3 are routing.
    for layer in (pcbnew.In1_Cu, pcbnew.In4_Cu):
        rect_zone(board, -W / 2, -H / 2, W / 2, H / 2 - ANT_DEPTH, [layer], net=net("GND"), name="GND")

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "ock_p1.kicad_pcb"
    pcbnew.SaveBoard(str(path), board)
    write_project(out_dir)
    print(f"placed {len(board.GetFootprints())} footprints, {len(nets)} nets -> {path}")
    return path


RULES = {
    "min_clearance": 0.09, "min_track_width": 0.09, "min_via_diameter": 0.25, "min_through_hole_diameter": 0.15,
    "min_via_annular_width": 0.05, "min_hole_to_hole": 0.2, "min_hole_clearance": 0.15,
    "min_copper_edge_clearance": 0.2, "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1,
    "min_silk_clearance": 0.0, "solder_mask_to_copper_clearance": 0.0,
}


def write_project(out_dir: Path):
    """KiCad reads DRC limits and net classes from the .kicad_pro, not the board."""
    import json
    pro = {
        "meta": {"filename": "ock_p1.kicad_pro", "version": 3},
        "board": {"design_settings": {
            "rules": RULES,
            "defaults": {"board_outline_line_width": 0.05},
            "rule_severities": {"silk_over_copper": "ignore", "silk_overlap": "ignore",
                                "silk_edge_clearance": "ignore", "text_height": "ignore", "text_thickness": "ignore"},
        }},
        "net_settings": {"classes": [{
            "name": "Default", "clearance": 0.09, "track_width": 0.09, "via_diameter": 0.25, "via_drill": 0.15,
            "microvia_diameter": 0.2, "microvia_drill": 0.1, "diff_pair_width": 0.1, "diff_pair_gap": 0.1,
            "wire_width": 6, "bus_width": 12, "line_style": 0, "schematic_color": "rgba(0, 0, 0, 0.000)",
            "pcb_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647,
        }], "meta": {"version": 4}},
    }
    (out_dir / "ock_p1.kicad_pro").write_text(json.dumps(pro, indent=2))
    import os
    rel = os.path.relpath(LIB, out_dir)
    (out_dir / "fp-lib-table").write_text(
        f'(fp_lib_table (version 7)\n  (lib (name "ock_p1")(type "KiCad")(uri "${{KIPRJMOD}}/{rel}")(options "")(descr "OCK-P1"))\n)\n')
    with (out_dir / "ock_p1_bom.csv").open("w") as f:
        f.write("ref,value,footprint,x_mm,y_mm,side\n")
        for ref, (fpid, value, _, (x, y, _r, side)) in PARTS.items():
            name = {"tab": "BatteryTab_1.2x2.0mm", "contact": "ContactPad_D1.6mm"}.get(fpid, None) if isinstance(fpid, str) else fpid[1]
            f.write(f"{ref},{value},{name},{x},{y},{side}\n")


if __name__ == "__main__":
    build(sys.argv[1], Path(sys.argv[2]))
