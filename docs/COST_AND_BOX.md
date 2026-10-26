# Cost and delivered-box specification

No live sensor or assembled-board quote has been obtained. The upstream
manufacturer-linked order pages returned HTTP 403 in this session. Do not treat
the numbers below as checkout prices or a completed purchase.

## What can be calculated now

The pinned upstream wearable BOM contains historical component prices at 10x
and 100x quantities. Multiplying populated quantities by those prices, excluding
rows marked do-not-install, gives:

| Population | Parts per board at 10x | Parts per board at 100x |
| --- | ---: | ---: |
| AVDD 3.6 V (matches exported schematic) | $42.7630 | $35.9138 |
| AVDD 3.0 V alternative | $43.0790 | $36.1569 |

Source: original spreadsheets in `vendor/biocoin/PCB/Biocoin/assembly/`.
This excludes PCB fabrication, setup, stencil, assembly, cell/harness, dock,
programming, bootloader, tests, electrode, coatings, case, shipping and tax.
It is an auditable historical subtotal, not current component availability.

Elmhurst Public Library publishes $0.10/g, $1 minimum, subject to eligibility and
its print rules: https://www.elmhurstpubliclibrary.org/3d-printing . The original
A0 base/lid solid model volumes total about 7.08 cm3; 100%-solid PLA at an assumed
1.24 g/cm3 would be about 8.8g before supports. Actual slicer mass, settings and
charged weight differ, so request the library's actual price. Local collection
is listed; it does not by itself meet mail delivery.

The Printed Bay advertises small parts from $13 with shipping or Des Plaines
pickup: https://www.theprintedbay.com/3d-printing-chicago/ . No price for these
files has been obtained. Compare delivered prices rather than headline print
prices; shipping can dominate a small enclosure order.

## Cheapest ordering strategy

1. Quote **two fully assembled readouts**, one reusable dock, and the smallest
   supplier-supported coated-electrode lot. Obtain separate 5/10/25 unit
   repeat prices; do not purchase a ten-pack solely because a link defaults to
   ten. Compare total first-order cash, not only per-unit pricing.
2. Keep the published readout layout unchanged for first articles. Removing
   unused multimodal circuitry to shave component cost would add redesign,
   layout and verification costs before the sensor works.
3. Use one simple planar electrode geometry and a disclosed existing supplier
   coating process. Avoid new nanoparticles or a custom insertion applicator
   in this first quote. Require factory-attached mating adapters where needed.
4. Use the published small-battery case for the first physical fit comparison;
   our flange/pad design is a separate A0 fit article. Select the cheapest
   service that can reproduce the required feature size and tolerance.
5. Assign one lead integrator final acceptance, software setup and shipment.
   Ask the sensor vendor whether it can take that role or subcontract the
   electronics job. Require subcontractor costs itemized in the quote.

## Budget model (unquoted planning allowance)

A useful comparison worksheet is **$500-$1,500 for first-article electronics,
one dock, battery/harnesses, bring-up, cases and shipping**, plus a **separately
quoted sensor-process/NRE and characterization job**. This allowance is an
estimate for screening quotes, not evidence that an assembled kit is available
at that price. The sensing-element development may exceed it substantially.
There is no defensible all-in price until a specialist accepts and prices the
coating, openness and acceptance requirements.

## Request the finished box, not loose surface-mount parts

The purchase description should explicitly include:

- Readout already populated, bootloaded, flashed, powered and dummy-cell tested.
- Cell with completed BM02B-ACHSS-compatible harness, verified polarity and
  charge settings; no soldering or crimping assigned to the recipient.
- Ready-to-mate coated electrode cartridges, labeled WE/RE/CE mapping and
  lot/calibration identity, plus controls and disclosed exposure history.
- Dock already assembled with pogo fixture and correct charge selection.
- Board/cell enclosure assembled or tool-free closure verified by the integrator.
- USB cable and any required screws/tools included; quote a single shipment
  after system integration, not independent untested subassemblies.
- Raw sensor characterization and end-to-end measurement report.
- Installed host software/launcher or exact supported setup package. No
  existing sensor protocol, cloud subscription or commercial CGM account is
  required for this design.

The result of that order would be a custom bench glucose-sensing kit. A
skin-inserted wearable CGM would require another validated sensor/process and
mechanical development stage; it is not hidden inside the enclosure quote.
