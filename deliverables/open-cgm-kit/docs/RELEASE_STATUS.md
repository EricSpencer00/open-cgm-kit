# A0 release status

This is an engineering review / supplier-quote package. It is not released for
human use or unreviewed manufacture.

| Item | Evidence now | Required before manufacturing release |
| --- | --- | --- |
| Readout schematic / routed board | Complete pinned Biocoin source, exports and BOMs | Reconcile stackup discrepancy; confirm component supply, BOM variant and export consistency |
| Readout manufacturing | Original Gerbers, drill, placement and native CAD | Assembler DFM, current quote, flash/test responsibility and procurement approval |
| Electrode geometry | Original 12x40 mm DXF, SVG and native routing review | Supplier DFM, dimensions/tolerances, 0.30mm tail stack, contact direction and actual mating check |
| Electrode chemistry | Proposed Pt/GOx/AgAgCl process and cited methods | Disclosed manufacturable formulation, coating parameters, bias/current characterization, raw measurements and acceptance contract |
| New enclosure/pad | Parametric CAD; watertight STL meshes and die-cut outline | Physical fit, fasteners, cell/antenna clearance, retention and print-material decision |
| Published enclosure | Original upstream CAD/STLs and board STEP | Fit to selected board/cell/harness and chosen manufacturing process |
| Bluetooth | Upstream device code plus new host CA bridge/parser | Hardware connection and on-board validation; acquisition metadata and integrity gaps below |
| Resilient | Executed host calibration tests and Python integration tests | Actual sensor calibration and metadata; embedded target integration if desired |
| Complete kit | Supplier work breakdown and unsent RFQ | Named lead integrator, quotes, spending/shipping authorization and receiving tests |

## Measurement protocol gap

The pinned upstream CA transport sends a little-endian float32 current stream
in microamperes. It has no device sample sequence, acquisition timestamp, or
concurrent temperature field. The source documents a possible dropped-byte
condition on TX overrun. Host receipt time and host sequence cannot establish
acquisition time or detect every plausible byte-loss-induced value.

The CA configuration's max-current field is an unused hint in this pinned
firmware, with inconsistent SDK/documentation units; CA RTIA is fixed at 10 kOhm.
It is not a current-protection limit. Disconnect does not automatically stop
the upstream acquisition; confirm stopped status during reconnection/recovery.

The new bridge logs measured raw current, labels missing metadata, and does not
emit a live glucose estimate. A future framed sensor protocol should carry
version, payload length, device sequence, acquisition time, raw current, actual
temperature and timestamp, sensor/calibration identity, status and an integrity
check. Session authentication/replay protection must be specified separately;
the presence of Bluetooth does not establish it. No such firmware revision has
been built or tested here. The upstream host GUI is available for bench current
visualization; the package does not claim a complete new mobile CGM app.

## Verification actually performed

- Checked copied upstream files against recorded SHA-256 hashes.
- Inspected real AFE schematic, BOM variants, J5 net map, battery and dock.
- Generated original electrode routes and checked connectivity/spacing and
  substrate containment; no native KiCad DRC/Altium ERC claimed.
- Checked serialized STL edge manifoldness, consistent winding, positive volume
  and bounding dimensions, and visually inspected the preview.
- Ran actual Resilient host typechecks, boundary tests and synthetic demo with
  installed rz 0.1.0; partial-proof warnings remain, no formal-proof claim.
- Ran sixteen Python bridge tests including real Resilient invocation and
  mocked acquisition lifecycle/cleanup; no physical
  Bluetooth device or electrode was present.

No coating was fabricated, glucose measured, battery charged, physical fit
checked, vendor contacted, files uploaded for manufacture, order placed or
money spent. These missing results are not replaced by CAD or software tests.
