# Open CGM Kit

A0 build and fabrication-request package for **our own glucose sensor**.
No Dexcom or Libre sensor is used as its glucose transducer.

The new work is the planar electrode/cartridge design, enclosure/pad CAD,
Resilient calibration core, and supplier integration specification. The complete
readout circuit is the openly licensed UCSD **Biocoin v1.3** design, preserved
unchanged with attribution and hashes. Reusing that proven measurement platform
avoids introducing an untested radio/analog circuit while developing the sensor.

**Current state: designed, sourced and software-tested; no hardware fabricated.**
This is a bench glucose-sensor first article. It is not a demonstrated
skin-inserted CGM. Supplier coatings/process disclosure, physical fit, calibration,
and sensor measurements remain open. There is no released inserter design.

## Open these files first

| Need | File |
| --- | --- |
| Real readout schematic | `vendor/biocoin/PCB/Biocoin/Schematic.PDF` |
| Editable circuit and routed PCB | `vendor/biocoin/PCB/Biocoin/design/` (Altium) |
| PCB fabrication | `vendor/biocoin/PCB/Biocoin/gerber/` |
| BOM and placement | `vendor/biocoin/PCB/Biocoin/assembly/` |
| Readout 3D CAD | `vendor/biocoin/fixtures/assets/Biocoin_v1.3.step` |
| Our electrode masks | `hardware/electrode_A0_layers.dxf` and `hardware/electrode_A0.svg` |
| Our native electrode routing review | `hardware/electrode_A0.kicad_pcb` |
| Our parametric mechanical CAD | `mechanical/open_cgm_A0.scad` and `mechanical/parameters.json` |
| Print files | `mechanical/generated/base_fit_prototype.stl` and `lid_fit_prototype.stl` |
| Adhesive-pad outline | `mechanical/generated/adhesive_pad_diecut_A0.svg` / `.dxf` |
| Previously published matching cases | `vendor/biocoin/fixtures/design/Small Battery/` |
| Resilient code and BLE bridge | `software/README.md` |
| Supplier handoff / local printing | `docs/FABRICATION.md` |
| Own-sensor chemistry and experiments | `docs/SENSOR_PROCESS.md` |
| Dry-lab electrode model and findings | `models/README.md` |
| Dexcom / Libre open auxiliary inventory | `docs/OPEN_HARDWARE_CATALOG.md` |
| Cost and smallest order | `docs/COST_AND_BOX.md` |
| Exact remaining release gates | `docs/RELEASE_STATUS.md` |

## Intended delivered box

1. One assembled, programmed, electrically tested readout with the correct
   rechargeable cell and completed keyed harness, installed in a verified case.
2. A small lot of our functionalized glucose-electrode cartridges and controls,
   with factory-finished mating tails/adapters and measured characterization.
3. One assembled charging/programming dock, USB cable and required fixture.

The assembler/integrator performs soldering, battery termination, firmware
installation, connector verification and bring-up. Eric connects a cartridge and
the dock. This is the requested delivery specification, **not an order that has
already been placed or a kit already tested**. One lead integrator must own final
assembly and end-to-end acceptance; two unrelated shops cannot leave that work
implicitly assigned to Eric.

## Bluetooth and Resilient

The pinned nRF52840 firmware implements the actual Biocoin GATT service,
configuration, start/stop, status, and raw current notification path. Full
upstream sources and host GUI are included. It does not need proprietary
Dexcom/Libre authentication.

`software/resilient/glucose_core.rz` implements calibration and sample-state logic
in Resilient. The host bridge calls the actual installed Resilient interpreter.
The nRF52 radio/AFE firmware remains upstream C/C++; this package does not claim
Resilient already runs the BLE stack on the MCU. Live acquisition is uncalibrated
raw current until the documented measurement metadata and calibration exist.

Run lightweight checks with an installed Resilient CLI:

```sh
RZ_BIN=/absolute/path/to/rz sh software/resilient/run_checks.sh
RZ_BIN=/absolute/path/to/rz python3 -m unittest discover -s software/bridge -v
RZ_BIN=/absolute/path/to/rz python3 software/bridge/biocoin_bridge.py --demo
```

The demo is synthetic. It is not evidence of a glucose measurement.

Regenerate the exact A0 CAD with Python 3.13 and `tools/requirements-cad.txt`, then run
`python tools/generate_cad.py`. The generator rejects changed dimension records
because its manually routed sensor layout must be revised and verified together.
The standalone OpenSCAD exposes editable mechanical parameters for exploratory
variants. The generator checks watertight mesh edges,
winding, volume, dimensions and electrode-net geometry. These checks do not
replace electrical DRC, supplier DFM, chemical testing or physical fit.

## Provenance and licensing

Upstream: https://github.com/ProfDrewHall/Biocoin at commit
`f723798118bb4f4d152acadf828b9ed18f3ca884`.
The 2026 paper is https://doi.org/10.1038/s44328-026-00103-z.

`vendor/biocoin/UPSTREAM_MANIFEST.json` identifies every copied file and SHA-256.
Upstream software/firmware are MIT, and its PCB/fixtures are CERN-OHL-W-2.0,
subject to more specific notices. Root licensing notice and README are retained.
Original hardware/mechanical work here is CERN-OHL-W-2.0; original software/tools
are MIT; original documentation is CC-BY-4.0. See `LICENSES/` and
`docs/ATTRIBUTION.md`. Proposed electrode chemistry has not yet been licensed or
released by a manufacturer. Third-party component/vendor documents retain their
own terms; bibliography links are not a license to reproduce proprietary designs.
