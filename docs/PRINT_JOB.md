# Enclosure fit-print job A0

Prepared job specification; not submitted. This archive is only for the dry
electronics enclosure fit prototype, not the sensing chemistry or skin insertion.

Print one each:

- `mechanical/generated/base_fit_prototype.stl`: 48 x 42 x 9.6 mm.
- `mechanical/generated/lid_fit_prototype.stl`: 43 x 34 x 1.6 mm.

Units are millimeters. Files are binary STL, independently checked for closed
edge topology, positive volume and consistent winding. No physical fit test has
been performed. The base has a 28.6 mm nominal internal cavity for a 26 mm board
envelope; it has no individually verified component standoffs/retention features.
Supplier must inspect board/cell/harness clearance and propose retention before
calling this an assembled device case. The published upstream small-battery CAD
in the full source archive is the comparison design for the actual board.

Suggested inexpensive first fit print: PLA FDM, flat base down, 0.16-0.20 mm
layers, no scaling, no metal-filled filament. Walls/floor are 1.6 mm nominal;
screw clearance 2.8 mm for proposed M2.5 hardware. Quote two M2.5 screws and nuts
after verifying engagement/length with the assembled parts; no fastener length
is released yet. Check the 1.0 mm-high coupon exit and bridge/support plan before
printing. This is not a tight snap-fit or a waterproof enclosure.

Request the shop's actual price, material, slicer mass, lead time and delivery.
Do not print `electrode_substrate_envelope.stl` as a glucose sensor. Do not
substitute the adhesive-pad drawing for a qualified adhesive/material decision.

## Elmhurst option

Official service: https://www.elmhurstpubliclibrary.org/3d-printing

Submission form:
https://elmhurstpubliclibrary.libwizard.com/id/f3c0958a924402bc05a21fd7322854e1

Published rate: $0.10/g, $1 minimum, subject to eligibility. This is a collection
service; request a commercial shipping quote if mail delivery is required.

## Mail delivery

The Printed Bay offers file upload and shipping from Des Plaines:
https://www.theprintedbay.com/3d-printing-chicago/

JLC3DP and PCBWay are alternatives linked in FABRICATION.md. No geometry has
been uploaded to them and no project quote has been received.
