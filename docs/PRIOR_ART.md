# Prior art: wired-enzyme and membrane patents

Research notes for the coating recipe (issue #9). Compiled 2026-10-26.

**This is not legal advice.** It is a technical literature survey by a non-lawyer.
Nothing here is a freedom-to-operate (FTO) opinion. Have a patent attorney review
before any product, sale, or clinical use. Bench research is not exempt from
infringement by default either.

## How status was determined

Bibliographic data, dates, assignment events and family lists were read from
Google Patents pages (fetched 2026-10-26). **No entry was verified against an
official USPTO status or legal-event record.** USPTO Patent Center and PPUBS are
interactive applications that could not be queried from this environment, and
maintenance-fee and certificate-of-correction records were not checked. Google's
"Adjusted expiration" lines are Google's estimate, not a legal conclusion.
The status column therefore uses two labels:

- **Google-adjusted**: Google shows an adjusted expiration date (which includes any
  patent-term adjustment Google has on file).
- **Inferred**: no adjusted date; I computed 20 years from earliest non-provisional
  filing (or, for pre-June-1995 filings, the longer of 20 years from filing or 17
  years from grant).

All entries are far enough in the past that any plausible term adjustment leaves
them expired, but each should still be confirmed on USPTO.

## Entries

### A. Heller / TheraSense / Abbott wired enzyme

| Number | Title | Assignee (at grant) | Priority / filed | Status |
| --- | --- | --- | --- | --- |
| US5262035 | Enzyme electrodes | E. Heller and Co (Heller) | 1989-08-02 | Google-adjusted 2015-11-16. Expired on any reading. |
| US5264104 | Enzyme electrodes | Heller; later TheraSense | 1989-08-02 priority, filed 1992-05-08 | Inferred 2010-11-23 (Google "anticipated"). |
| US5264105 | Enzyme electrodes | Vreeke / Heller; later TheraSense | 1989-08-02 priority, filed 1993-03-17 | Inferred 2010-11-23 (Google "anticipated"). |
| US5320725 | Electrode and method for the detection of hydrogen peroxide | Heller / TheraSense | 1989-08-02 priority, filed 1992-05-08 | Inferred 2011-06-14 (Google "anticipated"). |
| US6134461 | Electrochemical analyte sensor | Heller; later TheraSense/Abbott | 1998-03-04 | Inferred 2018-03-04. Continuations through 2014 exist; same priority date, so same nominal term. |
| US6175752 | Analyte monitoring device and methods of use | TheraSense | 1998-04-30 | Inferred 2018-04-30. Very large continuation family (to 2016 filings); the 20-year clock for continuations still runs from 1998-04-30. |
| US6329161 | Subcutaneous glucose electrode | TheraSense / Heller | 1993-12-02 (continuation) | Inferred 2013-12-02. Later assigned to NIH (2015, 2017 events). |
| US6605200 | Polymeric transition metal complexes and uses thereof | TheraSense / Abbott | 1999-11-15 (provisional), filed 2000-11-14 | Google-adjusted 2021-07-15. |
| US6605201 | Transition metal complexes with bidentate ligand having an imidazole ring and sensor constructed therewith | TheraSense / Abbott | 1999-11-15 (provisional), filed 2000-11-14 | Google-adjusted 2021-06-12. Continuations filed up to 2016. |

All nine numbers exist and match the titles above (checked on the Google Patents
page for each). The suggested numbers were all real; the titles in the issue
brief were not given, so the titles above are from the record.

**US5262035 / US5264104 / US5264105 (the foundational "wired enzyme" family).**
Discloses an electrode coated with a film in which a redox enzyme (GOx and others)
is covalently bound into a crosslinked, three-dimensional redox polymer with
multiple osmium-type redox centres. The enzyme is crosslinked with the polymer
using water-soluble multifunctional crosslinkers (polyethylene glycol diglycidyl
ether, PEGDGE, is the named example, plus carbodiimides, dialdehydes,
N-hydroxysuccinimide esters) in aqueous buffer between pH 3 and 9. Test examples
poise at +0.45 V vs SCE with phosphate/NaCl buffer. US5264104/5 add a
protein-excluding polymeric outer coating. Relevance: this is the usable
recipe skeleton if we ever move to second-generation (mediated) sensing. Our
current stack is first-generation (Pt, peroxide), so the direct use is limited to
the crosslinker choice (PEGDGE as an alternative to glutaraldehyde) and the
idea of a protein-excluding overcoat.

**US5320725.** Peroxidase immobilised in the same redox polymer network, used to
detect H2O2 / NADH at low potential. Relevance: the basis for the "Prussian blue
alternative" idea in spirit (peroxide reduction at low potential to avoid
interferents), but Prussian blue itself is a different chemistry; see gaps.

**US6329161 (Heller subcutaneous electrode).** The most useful Heller document
for us. Describes a 3 to 4 layer needle electrode deposited in a 20 to 150 um
recess on an insulated gold wire: sensing layer (wired GOx hydrogel), glucose
flux-limiting layer, biocompatible layer, and optionally a peroxidase
interferent-elimination layer. The stated design principle is that the recess plus
limiting layer reduce glucose transport to give linearity, with the electrode
reading roughly 2 to 30 mM glucose in vivo. About 5 ug of immobilised material
total. Relevance: confirms the architecture of our stack (flux-limiting layer
sets linear range) and gives a layer-count precedent.

**US6605200 / US6605201.** New osmium (and Fe, Co, Ru, V) complexes: polymeric
complexes in 6605200, biimidazole-based bidentate ligand complexes in 6605201,
used as lower-potential mediators so oxygen and interferents are not reacted.
Relevance: only for a future wired-enzyme variant. Synthesis of osmium
complexes is non-trivial and not a home-lab step.

**US6134461 / US6175752.** Sensor-structure and monitor-system patents
(recessed-channel conductive traces on a substrate; skin-mounted control unit).
Little coating chemistry. Relevance: electrode layout and system architecture
prior art, mostly mechanical/electrical, not recipe. These two have enormous
continuation families, so they are where an attorney should look first for
anything that survives.

### B. Early Dexcom, MiniMed/Medtronic and academic needle sensors

| Number | Title | Assignee | Priority / filed | Status |
| --- | --- | --- | --- | --- |
| US4484987 | Method and membrane applicable to implantable sensor | UC San Diego (Gough) | 1983-05-19 | Inferred 2003-05-19 (Google "anticipated"). |
| US4650547 | Method and membrane applicable to implantable sensor | UC San Diego (Gough) | 1983-05-19 priority, filed 1985-12-20 | Inferred 2004-03-17 (Google "anticipated"). |
| US4703756 | Complete glucose monitoring system with an implantable, telemetered sensor module | UC San Diego (Gough) | 1986-05-06 | Inferred 2006-05-06. |
| US4757022 | Biological fluid measuring device | Markwell Medical Institute | 1986-04-15 priority, filed 1987-11-19 | Inferred 2005-09-10 (Google "anticipated"). |
| US5165407 | Implantable glucose sensor | Univ. of Kansas (Wilson et al.) | 1990-04-19 priority, filed 1991-04-09 | Inferred 2010-04-19 (Google "anticipated"). |
| US5390671 | Transcutaneous sensor insertion set | MiniMed | 1994-03-15 | Inferred 2014-03-15. |
| US6001067 | Device and method for determining analyte levels | Dexcom (Shults, Updike et al.) | 1997-03-04 | Inferred 2017-03-04. |
| US6741877 | Device and method for determining analyte levels | Dexcom | 1997-03-04 priority, filed 2000-01-21 | Inferred 2017-03-04. |
| US6702857 | Membrane for use with implantable devices | Dexcom | 2001-07-27 | Inferred 2021-07-27. |
| US7226978 | Techniques to improve polyurethane membranes for implantable glucose sensors | Dexcom | 2002-05-22 | Inferred 2022-05-22. |
| US7192450 | Porous membranes for use with implantable devices | Dexcom | 2003-05-21 (provisional), filed 2003-08-22 | Google-adjusted 2025-03-23. Most recent entry; most worth a USPTO check. |

Assignee names above for the early patents are the original owner shown in
Google's event history; Google's "assignee" display lists current and
later-assigned parties and was inconsistent. Treat the assignee column as
indicative.

**US4484987 / US4650547 (Gough membrane).** Defines the problem our model
reproduces: body glucose is 50 to 100 times more abundant than oxygen, so a
naive enzyme electrode becomes oxygen-limited. Discloses a membrane that
combines hydrophilic paths (carrying the enzyme and passing both solutes) with
hydrophobic bodies permeable to oxygen but not glucose, so the glucose-to-oxygen
ratio inside is shifted to a slight oxygen excess. This is the origin of the
O2:glucose permeability-ratio design rule in `models/README.md`. No numeric
permeability recipe that we can copy directly, but the structural idea (an
oxygen-permeable hydrophobic phase such as silicone limiting a glucose-permeable
hydrophilic phase) is useful.

**US4703756.** Two-oxygen-electrode differential implantable module with a
telemetered system. Oxygen-detection architecture, not peroxide. Low relevance.

**US4757022.** Membrane-in-cartridge fluid measuring device (MiniMed/Markwell
lineage). Mostly device structure. Low relevance.

**US5165407 (Wilson et al., Kansas).** The most useful recipe document in this
group, a needle-type sensor on a Pt-Ir wire. It discloses: degrease the wire with
acetone, rinse, dry; dip in 5% cellulose acetate (39.8% acetyl) in 50:50
acetone/ethanol for 10 s, vapour exposure, second 10 s dip, air dry, as an inner
negatively-charged interference-rejecting layer (cellulose acetate or Nafion,
1 to 3 um); GOx attached via bovine serum albumin, crosslinked with
glutaraldehyde; and an outer membrane dip-coated from 4% polyurethane (Thermedics
SG 85A) in 98% THF / 2% DMF (10 uL held in a 2 mm wire loop, sensor passed
through). The outer polyurethane is estimated at 5 to 10 um and is stated to give
the diffusional glucose barrier that produces a linear response. An Ag/AgCl
reference is made by 0.4 mA/cm2 for 60 min in 0.1 N HCl. This maps almost
one-to-one onto our layer table (interference barrier, GOx/BSA/glutaraldehyde,
diffusion layer, Ag/AgCl RE). The membrane is described qualitatively; no
O2:glucose ratio is given.

**US5390671.** MiniMed slotted-needle insertion set for a thin-film sensor.
Insertion hardware only; irrelevant to a coupon bench stage.

**US6001067 / US6741877 (Dexcom, early).** Implant microarchitecture to deliver
blood flow to the sensor (vascularised sensor region). No usable coating recipe
for us. Relevance: low.

**US6702857 / US7192450 (Dexcom biointerface).** Two-domain biointerface
membranes: a tissue-ingrowth domain and a cell-impermeable domain. In-vivo
foreign-body-response solution. Not needed for the bench-coupon stage; relevant
only if the project reaches implantation.

**US7226978 (Dexcom polyurethane).** The closest thing to a published
membrane-tuning recipe in this set. Discloses blends of two polyetherurethaneurea
copolymers (one with a glucose permeability somewhat high, one somewhat low),
including a polyetherurethaneurea / polyetherurethaneurea-block-PEG blend (PEG
molecular weight 600 to 1500, about 20 wt% of the copolymer component), so
glucose permeability is tuned by composition. Membrane thickness 5 to 100 um,
preferably 20 to 60 um. Cast from solution; a roll-coated example (knife-over-roll,
0.012 inch gap, dried 120 to 150 C, film about 0.0015 inch / 38 um). Water-swollen
morphology is checked by an optical microscopy method. The permeability numbers
are given as relative tuning, not as an O2:glucose ratio. Relevance: direct
guidance for the permeability-tuning step the model says matters most.

### C. Classic academic needle-sensor papers (not patents)

Bibliographic details here were **not all verified**; confirm each before citing.

| Reference | Verified how | Why it matters |
| --- | --- | --- |
| Bindra, D.S. et al., "Design and in vitro studies of a needle-type glucose sensor for subcutaneous monitoring," Anal. Chem. 1991 (Wilson group, Kansas). A HAL repository record and a 1990 Arizona dissertation by Bindra (advisor G.S. Wilson) were found; volume/pages not confirmed. | Abstract confirmed via search | 26-gauge (0.45 mm) needle sensor, linear above 15 mM, response under 5 min, largely independent of O2 in the physiological range, good selectivity except against acetaminophen. A benchmark spec for our membrane and a confirmation that acetaminophen is the residual interferent. This is the academic twin of US5165407. |
| Gough, D.A. et al., "Two-dimensional enzyme electrode sensor for glucose," Anal. Chem. 57(10):2351-2357, 1985. | Citation confirmed via a patent record that cites it (EP0216467 family, US4890620); full text not read | Gough's two-dimensional diffusion design for oxygen/glucose balance. Note US4890620 (same inventor, priority 1985-09, not examined here) is the related patent. |
| Shichiri, M. et al., needle-type glucose sensor in a wearable artificial endocrine pancreas, Lancet 1982. | Not verified | Historic first needle-type subcutaneous GOx sensor. Cite from the primary source after checking. |
| Gough, D.A. et al., Sci. Transl. Med. 2010 (long-term implantable oxygen-based sensor). | Not verified | Later work; later patents likely cover it. Do not assume free. |

Academic papers are not patented, but a paper's recipe may be practised by a
patent that claims the same thing. Copyright covers the text, not the method.

## Usable formulations that appear free to practise

All statements are conditional on the status caveats above.

1. **Pt wire/electrode, cellulose acetate (about 5% in acetone/ethanol) or Nafion
   inner interference layer, 1 to 3 um, then GOx + BSA + glutaraldehyde, then an
   outer polyurethane dip layer** (US5165407 and Bindra/Wilson). Priority 1990;
   Google's anticipated expiration is 2010-04-19. The overall layer sequence is
   also the textbook stack described in the 1993-priority Heller document
   US6329161 background section.
2. **Outer-membrane composition tuning by blending two polyurethane (urea)
   copolymers with different PEG content**, and thickness windows of
   5 to 10 um (dip) or 20 to 60 um (cast) (US5165407, US7226978). US7226978's
   nominal term ends 2022-05-22.
3. **Hydrophobic-phase-limited oxygen-rich membrane concept** (US4484987,
   US4650547), nominal terms 2003 to 2004.
4. **Wired-enzyme redox polymer (Os polypyridine, PEGDGE crosslinking, poised near
   +0.3 to 0.45 V vs SCE)** (US5262035 family, US5264104/5, US5320725).
   Nominal terms 2010 to 2015. Only relevant if we leave first-generation
   sensing.
5. **Sensor layout and recessed-electrode design** (US6329161, US6134461,
   US6175752) nominal terms 2013 to 2018.

## What still seems encumbered or needs attorney review

- **Anything filed after about 2006.** Abbott (FreeStyle Libre / wired-enzyme
  improvements), Dexcom (resistance/interference domains, later membrane
  patents), and Medtronic have large later portfolios not examined here.
  Later continuations-in-part can claim new subject matter with later priority
  dates even when the parent is expired.
- **Continuation families of US6175752, US6134461, US6605201, US7192450.**
  Family members can carry later priority claims (CIPs) or patent-term
  adjustment; only USPTO records settle this.
- **US7192450.** Google-adjusted expiry 2025-03-23 is the newest; confirm on USPTO
  that no terminal disclaimer, reissue or later-priority sibling changes it.
- **Osmium complexes in particular** (US6605200/1 families). Synthesis is also
  hazardous (osmium compounds). Do not plan a wired-enzyme variant without
  review.
- **Prussian-blue working electrodes.** Not covered by the patents surveyed here
  and not searched. Needs its own prior-art search (Karyakin and others).
- **Specific commercial materials** (e.g. specific polyurethane grades) have
  supplier terms; supplier data sheets are not patents.
- Patent expiry does not remove regulatory requirements (FDA etc.); out of scope.

## Gaps

- No official USPTO legal-status verification was possible (see above). The
  issue's "verified" criterion is **not met** for any entry.
- Claims were not read line by line; the "what it discloses" notes come from
  abstracts and descriptions on Google Patents. An attorney reads claims, not
  descriptions.
- Dexcom/Brauker/Tapsak/Shults coverage is thin: US6702857, US7226978 and
  US7192450 were reviewed, but the Dexcom "resistance domain" and "interference
  domain" patents, and MiniMed/Mastrototaro sensor-coating patents
  (e.g. US5482473, US5568806 and relatives) were not retrieved.
- No permeability number reached us as an O2:glucose ratio from any source; the
  600:1 target in `models/README.md` still comes from our own model, not from
  literature.
- Shichiri 1982 and Gough 2010 citations unverified; Bindra 1991 journal
  details unverified.
