# Fabrication and supplier handoff

Status: fabrication brief prepared 2026-10-26. No files submitted, supplier
contact made, quote received, purchase made, or physical article validated.

The smallest useful first article is a **custom planar glucose electrode coupon
for a bench liquid cell**, delivered functionalized and connector-ready. It is fabricated
by a sensor specialist. The PCB manufacturer makes the electronic readout; the
3D-print shop makes the enclosure and dry coupon support. Neither ordinary PCB
fabrication nor 3D printing creates the sensing chemistry.

The first build has no inserter and is not inserted into a person or animal.
See [SENSOR_PROCESS.md](SENSOR_PROCESS.md) for the proposed sensing stack,
connector and acceptance experiments.

## Split the build into three jobs

| Job | Fabricator receives | Fabricator returns | Current readiness |
| --- | --- | --- | --- |
| Custom sensor | Dimensioned outline, electrode and passivation layers, J5 pad map, process brief, acceptance plan | Coated Pt/GOx three-electrode coupons, connector-ready tails/adapters, controls, drawings, storage instructions and raw measurements | RFQ specification; needs supplier design-for-manufacture review and quote |
| Readout electronics | Pinned Biocoin PCB manufacturing/assembly files, exact BOM, assembly drawing and firmware instructions | Assembled and flashed Biocoin readout with J5 input and tested electronic function | Source/design assets available; board stackup, assembly and sensor configuration require vendor confirmation |
| Housing and fixture | Watertight STLs in millimeters, assembly drawing, requested material and print notes | Dry enclosure/support pieces for fit inspection | Check the mechanical release status and dimensions before submission |

Keep liquid-contact parts compatible with the experiment and keep the dry
electrical interface out of the bath. An enclosure print has no demonstrated
waterproofing, sterility or sustained skin-contact suitability merely because
its shape resembles a wearable.

## Electronics fabrication brief: Biocoin readout

Use the pinned [Biocoin open hardware](https://github.com/ProfDrewHall/Biocoin)
assets held in `vendor/biocoin/`. The upstream design includes an nRF52840 and
AD5940, manufacturing outputs, firmware, host software and mechanical files.
Retain its applicable license and provenance. This readout measures our own
electrode; it does not require a commercial CGM sensor or its proprietary app.

Ask a PCB assembly/embedded-development vendor for an **assembled, programmed,
tested board**, not bare PCBs. Quote two first-article boards and separate
repeat pricing at five boards, using the supplied revision and exact BOM. The
supplier must return a DFM report, assembly drawing and substitutions for review
before any manufacture. Do not mix the docking-station files with the wearable
board files or assume a current BOM matches an older export.

The project inspection found a board-thickness discrepancy between a published
0.8 mm specification and approximately 0.94 mm inferred from the PCB-source
stack. The fabricator must resolve the actual stackup and connector/mechanical
fit from the supplied sources; neither number is a released build instruction.

Include BOM procurement, assembly, programming interface, bootloader/firmware
build and flash, power/battery provisions, host connection instructions and
test labor in the quote. Supply exact firmware source revision, toolchain,
build commands, produced image/hash and configuration. No firmware image has
been hardware-validated by this project yet. The vendor should validate:

- Power-up and safe supply/current behavior, firmware startup and BLE logging.
- AD5940 measurement using traceable dummy-cell/resistor inputs before liquid.
- J5 continuity and orientation using the agreed mating FPC drawing.
- Chronoamperometry with the intended **WE1/J5-14, RE0/J5-7, CE0/J5-8** routing,
  correct current sign, reported units, timestamping and suitable current range.
- The supplier-recommended sensor bias against its specified reference, with
  no unexamined assumption that an upstream demonstration's settings suit GOx/Pt.

The sensor fabricator and board assembler must agree the tail/adaptor and
signal mapping before either job is released. A test report on a dummy cell
verifies electronics, not glucose performance. If the assembler does not offer
firmware bring-up and testing, quote a named integration service rather than
leaving those steps silently assigned to the end user.

## Cheapest plausible development route

The cost-minimizing hypothesis is **one planar geometry, one established
supplier coating process, a small first lot and an external liquid cell**.
Avoid wafer-scale fine features, tiny implanted filaments, custom applicators
and multi-analyte chemistry in this order. Have each supplier quote a stock
process with our contour/pad map and a separately priced fully custom process.

Request **10 functionalized coupons plus 3 matched no-GOx controls**, and
separate repeat-lot prices for 25 and 100 functionalized units. Ask for the
supplier's actual minimum economical quantity if it differs. Controls have the
same substrate, electrode, passivation and membrane processing, omitting GOx
only as agreed and documented. Supplier characterization should use designated
units, with the remaining delivered units' prior exposure clearly stated.

No supplier has quoted this project. There is no verified cheapest sensor
vendor, minimum order, lead time or delivered price. Separate tooling/NRE,
blank-electrode fabrication, functionalization, connector tail/adapter, testing,
packaging, shipping, taxes and repeat orders in every quote. A budget allowance
is not a vendor quote.

## Specialist sensor suppliers: verified capability, not an order

### Zimmer and Peacock — ask for an end-to-end coated sensor quote

Its official [contract CGM development page](https://www.zimmerpeacocktech.com/2017/11/27/zp-contract-cgm-development-and-manufacturing/)
advertises sensor development/manufacturing and explicitly discusses linearity,
signal stability and interferents. Its [glucose-sensor page](https://www.zimmerpeacocktech.com/products/glucose-sensors/)
offers glucose sensors for continuous or discrete measurements. The
[external-use sensor datasheet](https://s46c23316fd696b31.jimcontent.com/download/version/1705675764/module/12481086098/name/GLUCOSE%20SENSOR%20DATASHEET%20EXTERNAL%20USE.pdf)
offers customization of electrode configuration, geometry and materials and
states that the product has not been tested for biocompatibility.

Best fit: obtain one accountable fabrication, coating, packaging and
characterization package. Confirm Pt-based chemistry, separate WE/RE/CE,
connector-ready tail, small-run availability and publishable process terms. The
advertised capability does not confirm that it accepts this specific design or
will disclose its formulation. Use the contact route on the official page only
after authorization to contact suppliers.

### Metrohm DropSens — ask for custom electrodes plus GOx functionalization

[Custom-made solutions](https://metrohm-dropsens.com/custom-made-solutions/)
covers custom electrochemical sensor development and production. Its
[DRP-550 platinum electrode](https://metrohm-dropsens.com/products/electrodes/screen-printed-electrodes/screen-printed-platinum-electrode/)
has Pt working/counter electrodes and a silver reference; the page offers
customization of geometry, substrate, size and ink. Its
[DRP-GLU10 glucose electrode](https://metrohm-dropsens.com/products/electrodes/modified-screen-printed-electrodes/screen-printed-electrodes-for-glucose-detection/)
demonstrates commercial enzyme modification and batch calibration, but uses a
ferrocyanide/GOx/carbon working electrode rather than our proposed Pt/peroxide
route.

Best fit: ask whether its existing Pt process can be supplied with our agreed
GOx/interference/diffusion stack and mating interface. Do not order bare DRP-550 and call it
a glucose sensor, or silently treat GLU10's chemistry and silver reference as
identical to our proposed design. The site's custom-solutions page contains the
actual request form and official contact route.

### MicruX — strong geometry/manufacturing candidate; confirm coating scope

Its [printed-electrode capability](https://www.micruxfluidic.com/custom-solutions/printed-electrodes-manufacturing/)
lists PET/alumina substrates, platinum and Ag/AgCl inks, and short runs. Its
[thin-film capability](https://www.micruxfluidic.com/custom-solutions/thin-film-electrodes-manufacturing/)
lists Pt/Au on glass, 150 ± 15 nm metal, and SU8/PI protection. These are verified
electrode-manufacturing options. End-to-end GOx coating and a disclosed
ready-to-connect glucose process for this project remain unconfirmed.

Best fit: price the planar printed coupon first. Ask explicitly whether MicruX
will perform functionalization, characterization and connector integration itself or
name an accountable partner. Buying blank electrodes and hoping another shop
can coat them leaves an unresolved integration job.

### Pinnacle — useful reference/control lead, not the default custom coupon

Its official [glucose-biosensor page](https://www.pinnaclet.com/glucose.html)
describes enzyme-generated peroxide detection on Pt-Ir and selective membranes
for rodent research. Its [preclinical CGM page](https://www.pinnaclet.com/continuous-glucose-monitoring-systems.html)
describes a complete animal-research system. These establish relevant technical
experience, not availability of our custom planar three-electrode coupon or
human use. Ask only if a reference sensor or suitable custom external sensor is
needed; avoid paying for an entire preclinical wireless system as the first step.

## Local enclosure/fixture printing

Elmhurst/Chicagoland is an assumption for these options, not a confirmed address
or confirmed library eligibility.

### Lowest published local rate: Elmhurst Public Library

The current [3D-print service page](https://www.elmhurstpubliclibrary.org/3d-printing)
lists **$0.10 per gram, $1 minimum**, up to seven business days, 10 hours per
print, and five printed items per month. It uses PLA on a Bambu Lab X1C,
0.16 mm layers and 15% grid infill. Eligibility includes the specified library
cardholders and Elmhurst-affiliated students/teachers. Address: 125 S. Prospect
Avenue, Elmhurst, IL 60126.

To submit when authorized:

1. Export each mechanical part as its own watertight STL in millimeters. Check
   the dimensions against the assembly drawing and verify that the pieces fit
   within 225 × 225 × 225 mm. Do not upload electrode drawings as a print job.
2. Open the [official submission form](https://elmhurstpubliclibrary.libwizard.com/id/f3c0958a924402bc05a21fd7322854e1),
   linked by the service page. Its live accepted-file filter was not inspectable
   without JavaScript; STL is specified in the library's published handout.
3. Request PLA, one of each required part, and identify which surfaces need
   usable fit. Include the intended dimensions and note that this is an external
   bench electronics fixture, not an implant or sterile medical component.
4. Follow the library's eligibility and collection instructions. Pay the quoted
   weight-based fee and inspect the fit before using the support near liquid.

Example only: a finished 10 g print would be $1 at the published rate. Actual
charge depends on the library's charged weight and its interpretation of
multiple parts. No part weight or enclosure price has been measured here.

### Commercial local alternatives

- [The Printed Bay, Des Plaines](https://www.theprintedbay.com/3d-printing-chicago/)
  advertises STL/3MF/OBJ/STEP upload, free Des Plaines pickup or shipping,
  typical 3–5 business days, and small parts from $13. The actual enclosure price
  requires a model quote.
- [3D Printing Chicago](https://www.3d-printing-chicago.com/) advertises an online
  instant quote, northwest Chicago pickup or shipping, and PLA/PETG/ABS/nylon,
  flexible filament and resin options. No project price obtained.

### Mail-order alternatives

| Service | Submission route and formats | Cost evidence |
| --- | --- | --- |
| [JLC3DP](https://jlc3dp.com/3d-printing-quote?queryMaterialTechnicsId=1) | STL/STP/STEP/OBJ/3MF; [instructions](https://jlc3dp.com/help/article/how-to-place-a-3d-printing-order), [shipping](https://jlc3dp.com/shipping) | Advertised SLA starting at $0.30, FDM/nylon at $1; these exclude a verified project geometry/delivery quote |
| [PCBWay](https://www.pcbway.com/rapid-prototyping/manufacture/) | STL/OBJ/STEP/STP for printing; [official FAQ](https://www.pcbway.com/rapid-prototyping/cnc-faq.html) | Quote required; no project price obtained |
| [Craftcloud](https://craftcloud3d.com/en/upload) | STL/OBJ/3MF/STEP/STP and other formats; 500 MB maximum; shipping comparison | Quote required; no project price obtained |

For initial FDM supports, 1.6 mm walls and a small fit coupon are sensible design
choices, subject to the released model and the chosen printer.
[JLC's official guide](https://jlc3dp.com/help/article/3d-printing-design-guideline)
lists overall small-part tolerances of ±0.3 mm for FDM/nylon and ±0.2 mm for SLA;
these are not proof that an arbitrary press-fit will work. Standard resin and
PLA are not automatically suitable for wet chemistry or prolonged skin contact.

## Sensor supplier RFQ — prepared for review, not sent

**Subject: Small-lot custom planar GOx/Pt glucose sensor for external bench testing**

Please quote fabrication, functionalization, connector integration and bench
characterization of our custom planar glucose-sensor coupon. The intended use
is measurement in a controlled external liquid cell. No human/animal insertion,
applicator, sterility claim, or clinical performance claim is requested.

Please review the attached revision-controlled outline, electrode/passivation
layers and contact map, together with SENSOR_PROCESS.md. Return DFM changes
before manufacture. We propose a Pt WE, separate Pt or carbon CE, integrated
Ag/AgCl pseudo-RE, immobilized GOx, interference rejection and a glucose-flux
membrane. Please identify any proposed change to the sensing mechanism.

The proposed coupon body is 12 × 40 mm. The dry mating tail is 10.5 mm wide,
with 20 contacts at 0.50 mm pitch, 0.35 mm pad width and 3 mm exposed pad length;
nominal total tail thickness is 0.30 mm including its stiffener. It mates to
Biocoin J5, Molex 5034802000. Pin 7 is RE0, pin 8 CE0, pin 14 WE1; all other
coupon contacts are unconnected. The dimensioned drawing governs orientation
and geometry. These dimensions need your DFM and current connector-drawing
review; fit has not been measured. If your electrode process cannot produce
this tail directly, quote a factory-attached FPC adapter, strain relief and
end-to-end continuity/retention testing. Deliver a complete mating assembly.

Quote 10 functionalized units and 3 matched no-GOx controls, plus repeat-lot
prices at 25 and 100 functionalized units. Suggest your minimum economical
quantity if these quantities are unsuitable. Deliver sensors coated, packaged
and ready to connect. Please quote connector-tail/adapter work separately and
confirm compatibility with your actual substrate and contact materials.

Please provide:

- Tooling/NRE, unit price, functionalization, controls, tests, tail/adapter, packaging,
  shipping, taxes, payment terms, minimum order and lead time as separate items.
- As-built geometry, layer stack and critical material/process specifications;
  manufacturing yield/replacement terms and the ownership/disclosure terms for
  drawings, formulations, protocols and raw data. Our objective is an open,
  reproducible sensor process; flag proprietary steps before accepting the job.
- GOx source/activity, substrate/electrode/passivation materials, coating
  deposition/cure/wash process, storage temperature, shelf life and shipping
  conditions, including whether units are shipped dry or hydrated.
- Integrated-reference potential/drift versus a stated laboratory reference;
  required pH/chloride/temperature/oxygen conditions; recommended potential,
  polarity, background current, sensitivity, current range and hydration time.
- Raw glucose calibration and dynamic-response data, blank/no-GOx controls,
  initial repeatability and 24-hour drift; achievable usable range toward a
  target of 2–25 mM and honest limits if the first formulation is narrower.
- Interference test concentrations and raw responses for acetaminophen,
  ascorbate and urate; effects of temperature, oxygen and a specified
  protein-containing synthetic medium. Agree pass/fail thresholds before work.
- Clear identification of which delivered units were already exposed during
  characterization and which are unused; all failed units/results retained in
  the report rather than silently excluded.

Please propose the least expensive existing process that can meet this scope,
and identify what additional development remains. This request seeks a quote
and feasibility assessment; it is not authorization to begin paid work.
