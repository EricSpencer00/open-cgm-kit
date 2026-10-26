# Sensor process: a custom glucose electrode, made for the bench

Status: proposed first-article process, 2026-10-26. No electrode has been made,
functionalized, measured, or validated for this project. The drawing and the
layers below are an RFQ input, not a proven manufacturing recipe.

The first sensor is a **flat, blunt, three-electrode coupon for a small liquid
test cell**. A specialist fabricates the electrodes, applies the glucose-sensing
chemistry, supplies the electrical interface, and delivers a ready-to-connect
sensor. This is the project's own sensor development; an off-the-shelf glucose
sensor is useful only as an optional control.

This revision has no skin insertion, applicator, animal experiment, or human
experiment. Passing the bench gates does not establish a CGM for treatment use.

## Measurement mechanism

Use first-generation amperometry as the baseline: immobilized glucose oxidase
(GOx) consumes glucose and oxygen, producing hydrogen peroxide. A potentiostat
holds the platinum working electrode (WE) at a specified potential relative to
the reference electrode (RE), and measures the current associated with peroxide
oxidation. A separate counter electrode (CE) carries the cell current.

Record current first. A conversion into glucose concentration requires a
measured calibration for the particular sensor, medium, temperature, oxygen
condition, and age. PCB copper, an enzyme label, or a glucose-dependent signal
alone is insufficient evidence of a quantitative sensor.

## Proposed layer stack

| Layer or feature | First-article proposal | Supplier must return |
| --- | --- | --- |
| Substrate | Flat 12 × 40 mm coupon; PET sensing body with a connector-compatible tail or preattached FPC adapter | Material grade, thickness/tolerance, solvent and cure compatibility, actual bend limits |
| Conductors | Printed or deposited routing under insulation | Material and thickness, resistance, adhesion and continuity results |
| WE | Exposed platinum sensing area | Geometric area, surface treatment, roughness or electroactive-area characterization, peroxide response |
| CE | Separate Pt; carbon may be quoted as a cost alternative | Material/area and evidence that CE capacity does not limit the intended experiment |
| RE | Printed Ag/AgCl pseudo-reference in the wet region | Ink/composition, chloride conditions, potential versus a laboratory reference, drift and hydration instructions |
| Passivation | Chemically compatible dielectric over traces, with wet electrode windows and dry contacts open | Materials, layer thickness, window registration and soak/leakage data |
| Interference barrier | Supplier-qualified peroxide-permeable interference-rejection layer | Composition/process and measured responses to acetaminophen, ascorbate, and urate |
| Enzyme layer | Immobilized GOx, with a disclosed stabilizer/crosslinker system appropriate to the substrate | Enzyme source/activity/lot, formulation, deposition area and amount, cure, wash, retention and storage process |
| Diffusion layer | Tuned glucose-flux-limiting membrane compatible with GOx and oxygen transport | Composition, deposition method, thickness, sensitivity/linearity/oxygen tradeoff and response time |
| Dry interface | 20-contact, 0.5 mm-pitch tail mating to Biocoin J5; only pins 7, 8 and 14 used in this variant | As-built pad map, contact orientation, actual thickness/stiffener, adapter if required and final continuity inspection |

This stack is a development proposal. Layer order and chemistry must be agreed
with the fabricator and captured in the released process revision. A membrane
that rejects one interferent does not establish rejection of all interferents.
An Ag/AgCl ink pseudo-reference is not equivalent to a stable, filled laboratory
Ag/AgCl reference electrode.

### Electrical interface

Use three named nets throughout: **WE, RE, CE**. Do not connect RE and CE
together. The electronics baseline is the open
[Biocoin platform](https://github.com/ProfDrewHall/Biocoin), with J5
[Molex 5034802000](https://www.molex.com/en-us/products/part-detail/5034802000).
Molex lists 20 circuits, 0.50 mm pitch and dual contacts. Its stated maximum
mating durability is 10 cycles; do not repeatedly use one connector as an
unlimited-life development fixture.

| J5 pin | Board net | Coupon function |
| --- | --- | --- |
| 7 | RE0 | Ag/AgCl reference |
| 8 | CE0 | Pt counter |
| 14 | WE1 | Pt glucose working electrode |
| All others | Other board nets | Leave unconnected on the coupon |

The proposed tail is 10.5 mm wide, 20 pads at 0.50 mm pitch, 0.35 mm pad width,
3 mm exposed contact length, and 0.30 mm total tail thickness including its
stiffener. These are **DFM proposal dimensions**, not verified mating results.
The nominal electrode drawing defines the contact-side view, insertion
direction and pin numbering. Radii and manufacturing tolerances remain for
supplier DFM. Supplier must check these against
the connector manufacturer's current mating-cable drawing and the actual board.
Mirroring the tail would connect the wrong electrodes even with a dual-contact
connector.

Request delivery with a connector-compatible tail already attached or integrated.
If the electrode process cannot form these pads and thickness, quote a
factory-attached FPC interposer with strain relief, tested end-to-end. For
example, MicruX lists a 500 µm minimum printed dimension; the proposed 350 µm
pads and 200 µm routes are below that published limit. A supplier must accept a
capable thin-film process, or return wider sensing-body routes with a separately
fabricated fine-pitch adapter as an explicit design revision. A loose, unsupported film or
three loose wires is not the requested connector-ready first article. Do not
solder directly to printed sensing ink. Test insertion, retention, continuity
and insulation using the agreed adapter/connector fixture before release.

See `hardware/electrode_A0_drawing.svg` (also PNG) for the dimensioned nominal
review sheet. The A0 wet features are a 1.2 mm-diameter Pt WE centered at (8.5, 33) mm, a
1.2 × 3 mm Ag/AgCl RE centered at (3.3, 33) mm, and a 1.4 × 6 mm Pt CE centered at
(5.5, 33) mm. Origin is the lower-left of the full body envelope with the dry
tail at y=0. See `hardware/electrode_A0_layers.dxf`, the native review layout
`hardware/electrode_A0.kicad_pcb`, and `mechanical/parameters.json`.
The SVG artwork is 1:1 in millimeters and is viewed from the contact side with
the dry tail at the bottom. Pin 1 is on the left in that view; the supplier must
map it to the actual board connector orientation. Supplier must confirm active-area tolerances,
coating registration and the mechanical contour before fabrication.

## Public process references

These papers justify the approach and identify experiments. They do not validate
this project's geometry or supply a license to third-party patents.

1. [Du et al., 2015, *Fabrication of a Flexible Amperometric Glucose Sensor Using
   Additive Processes*](https://pmc.ncbi.nlm.nih.gov/articles/PMC4664458/),
   DOI [10.1149/2.0101504jss](https://doi.org/10.1149/2.0101504jss).
   Demonstrates patterned Pt and Ag/AgCl on polyimide, printed GOx, and a
   diffusion-control membrane. The paper characterizes glucose response and
   acetaminophen interference in vitro. Its combined reference/counter and
   multiple working electrodes differ from our separate three-electrode coupon.
   Transfer the process concepts, not the published performance claims.
2. [*Design and Fabrication of a High-Performance Electrochemical Glucose
   Sensor*, 2011](https://pmc.ncbi.nlm.nih.gov/articles/PMC3208859/).
   Compares enzyme-coated Pt with added protective layers. The unbounded
   enzyme reaction saturates at low glucose; a glucose-flux-limiting membrane
   extends linearity while reducing sensitivity. This is why the membrane is a
   measured process variable rather than an optional decorative coating.
3. [*Electrochemical Glucose Biosensor of Platinum Nanospheres Connected by
   Carbon Nanotubes*, 2009](https://pmc.ncbi.nlm.nih.gov/articles/PMC2864166/).
   Uses GOx immobilization and a three-electrode peroxide-measuring arrangement.
   Its nanostructured surface is a different implementation; the project does
   not require CNT fabrication to start.

The initial supplier process should use its existing qualified tools and
materials. Introducing custom nanoparticles, custom printing equipment, new
enzyme chemistry, and a new membrane simultaneously would make failed results
harder to diagnose. A simpler validated supplier process is preferable, subject
to the public-disclosure requirements below.

## Supplier-owned manufacturing sequence

1. Review the dimensioned coupon and layer drawings. Identify process limits,
   minimum feature sizes, dielectric registration and pad attachment method.
   Return a marked-up drawing before tooling.
2. Fabricate the substrate outline and electrode routing. Inspect dimensions,
   metal continuity, electrode area and separation.
3. Apply dielectric/passivation, leaving only the defined electrode windows and
   dry pads exposed. Check adhesion and leakage after soaking in the test medium.
4. Prepare and characterize the Pt surface. Establish peroxide sensitivity and
   potential dependence using unfunctionalized controls.
5. Apply the agreed interference barrier and immobilized GOx stack. Record
   materials, lots, deposition parameters and storage/handling conditions.
6. Apply the diffusion membrane. Measure glucose response and oxygen dependence;
   adjust only through an identified process revision.
7. Complete the connector-compatible dry tail or preattached FPC adapter, inspect
   pin mapping and strain relief, package individually, and supply storage
   conditions and shipping limits.
8. Deliver all units, including controls, with raw acceptance data, sample IDs,
   an as-built drawing and deviations from the proposed specification.

Specialist laboratory work includes the coating solvents, enzyme handling,
crosslinking, membrane formation and electrode chemistry. This kit does not
require the user to buy or manipulate those fabrication reagents at home.
Shipping a blank Pt electrode without these steps does not fulfill the
ready-to-connect glucose-sensor scope.

## Bench characterization and promotion gates

The values below are **proposed engineering targets**, to negotiate before
ordering. They are not medical-device acceptance criteria or achieved results.

| Stage | Experiment | Proposed evidence to advance |
| --- | --- | --- |
| Electrical | Inspect coupon; verify each J5 contact to its named electrode; inspect for interelectrode shorts and dielectric failures | Supplier report plus receiving inspection; all delivered functional units mapped correctly |
| Cell baseline | Hydrate using supplier instructions; compare integrated RE against a separate laboratory Ag/AgCl reference | Record offset, drift, pH, chloride, temperature and oxygen; no unexplained discontinuity |
| Transducer control | Run bare Pt and no-GOx controls, plus a supplier peroxide check | Show that glucose sensitivity requires active GOx; report background and electrode response separately |
| Static glucose | Independent standards at 0, 2, 5, 10, 15, 20 and 25 mM, plus a descending series | Monotonic response; explicitly identify usable range, residuals, hysteresis and saturation; target ≤15% concentration error over a negotiated bench range |
| Repeatability | At least five functional coupons; replicate standards | Report all units and failures; target sensitivity CV ≤15% for this first lot |
| Dynamics | Independent low/high steps with controlled mixing or flow | Measure uncorrected delay and t90; initial target t90 ≤120 s under the recorded cell conditions |
| Drift | Continuous 5 mM exposure for 24 h, followed by repeat calibration | Initial target sensitivity change ≤10%; report baseline drift separately and preserve failed traces |
| Environment | Repeat relevant standards at controlled temperatures and dissolved-oxygen conditions | Quantify each effect; demonstrate that ordinary oxygen variation cannot masquerade as glucose without detection |
| Interference | Separate and combined acetaminophen, ascorbate and urate challenges at predeclared concentrations | Report current change and glucose-equivalent error; concentrations and limits must be agreed, not selected after seeing results |
| Complex medium | Repeat in a specified protein-containing synthetic interstitial-fluid medium | Measure added fouling, drift and selectivity effects; do not imply equivalence to living tissue |
| Replication | Repeat an agreed subset on at least three independently fabricated lots | Show process reproducibility and publish lot variation before a wearable sensor development decision |

Use an independently prepared blinded concentration series to test the
calibration. Random sample splitting within one sensor's time series does not
test a new sensor or a new fabrication lot. Record the raw amperometric signal,
temperature, oxygen/mixing conditions, reference identity, sample additions,
calibration version and exclusions. Fit a simple calibration before considering
more elaborate algorithms.

Set the operating potential only after the supplier provides peroxide response,
interference and reference-electrode data. Literature values near +0.6 V versus
Ag/AgCl are starting hypotheses; they do not automatically apply to an ink
pseudo-reference or a different membrane. Ask for expected background/current
range and ensure the chosen potentiostat has sufficient bias and current range.

## What must be open

Before a supplier is selected, resolve whether we can publish the electrode
geometry, masks, materials, critical process parameters, layer specifications,
test protocol, calibration code and raw characterization data. Ask the supplier
to distinguish its background IP from project-owned work and identify any
disclosure restrictions in the quote. A secret coating can be an external
comparison device; it cannot be represented as a fully reproducible open sensor.

Do not describe the project as a working CGM until measurements support that
specific claim. The near-term release is a documented sensor-fabrication design
and external-liquid experiment. Shelf life, sterility, tissue compatibility,
insertion mechanics, long-term wear, clinical accuracy and treatment decisions
remain separate future development questions.
