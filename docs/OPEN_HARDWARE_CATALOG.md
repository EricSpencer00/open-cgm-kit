# Open CGM hardware and protocol source catalog

Checked 2026-10-26. This is a targeted source inventory, not a claim that every
public CGM project has been found. A public paper, readable repository, protocol
implementation, and an openly licensed manufacturing package are different
deliverables. None of the auxiliary readers below supplies a new glucose-sensing
filament or validates this project's custom electrode chemistry.

## Own-sensor readout: Biocoin

[Biocoin](https://github.com/ProfDrewHall/Biocoin) is the most useful verified
starting point for the project's own sensor electronics. UC San Diego's BioEE
group provides an AD5940 electrochemical analog front end, nRF52840 Bluetooth Low
Energy controller, power system, firmware, host software, docking station, and
mechanical fixtures. The [2026 paper](https://doi.org/10.1038/s44328-026-00103-z)
reports electrical/electrochemical platform characterization. It does not validate
a finished clinical CGM or this project's electrode cartridge.

The source inspection used upstream commit
`f723798118bb4f4d152acadf828b9ed18f3ca884`. The wearable PCB is **v1.3**; the
docking station project is **v1.0**. The exported wearable schematic is dated
2026-03-11. Source assets should stay pinned together rather than mixing a later
BOM with an earlier fabrication export.

| Deliverable | Exact upstream asset at the inspected revision |
| --- | --- |
| Wearable schematic PDF | [`PCB/Biocoin/Schematic.PDF`](https://github.com/ProfDrewHall/Biocoin/blob/f723798118bb4f4d152acadf828b9ed18f3ca884/PCB/Biocoin/Schematic.PDF) |
| Editable wearable design | [`PCB/Biocoin/design/`](https://github.com/ProfDrewHall/Biocoin/tree/f723798118bb4f4d152acadf828b9ed18f3ca884/PCB/Biocoin/design): `Biocoin_v1.3.PrjPcb`, `Biocoin_v1.3.PcbDoc`, `AFE.SchDoc`, `Power Management.SchDoc`, `MCU_BLE_Module.SchDoc`, `Current_Source.SchDoc`, harness and output-job files |
| Fabrication exports | [`PCB/Biocoin/gerber/`](https://github.com/ProfDrewHall/Biocoin/tree/f723798118bb4f4d152acadf828b9ed18f3ca884/PCB/Biocoin/gerber): copper/mask/paste/outline/mechanical Gerbers, `Biocoin_v1.3.TXT` drills, `.DRR`, `.REP` and `.EXTREP` reports |
| Assembly | [`PCB/Biocoin/assembly/`](https://github.com/ProfDrewHall/Biocoin/tree/f723798118bb4f4d152acadf828b9ed18f3ca884/PCB/Biocoin/assembly): `BOM_Final_Biocoin_v1.3_AVDD=3.0V.xlsx`, `BOM_Final_Biocoin_v1.3_AVDD=3.6V.xlsx`, `Pick_and_Place_Assembly_Biocoin_v1.3.txt` |
| Docking station | [`PCB/Docking Station/`](https://github.com/ProfDrewHall/Biocoin/tree/f723798118bb4f4d152acadf828b9ed18f3ca884/PCB/Docking%20Station): schematic PDF, editable `Biocoin_Motherboard_v1.0.PrjPcb` and `Biocoin_Motherboard.PcbDoc`, Gerbers, `BOM_Final_DockingStation_v1.0.xlsx`, pick-and-place file |
| Shared ECAD libraries | [`PCB/Shared Libraries/`](https://github.com/ProfDrewHall/Biocoin/tree/f723798118bb4f4d152acadf828b9ed18f3ca884/PCB/Shared%20Libraries): `Modules.SchLib`, `Modules.PcbLib`, `Schlib.SchLib`, `PcbLib.PcbLib` |
| Board 3D model | [`fixtures/assets/Biocoin_v1.3.step`](https://github.com/ProfDrewHall/Biocoin/blob/f723798118bb4f4d152acadf828b9ed18f3ca884/fixtures/assets/Biocoin_v1.3.step) |
| Enclosures and dock fixtures | [`fixtures/`](https://github.com/ProfDrewHall/Biocoin/tree/f723798118bb4f4d152acadf828b9ed18f3ca884/fixtures): SOLIDWORKS assemblies/parts, small- and large-battery STL variants, `fabrication/Holder - rev 6.STL` |
| Firmware and BLE host | [`firmware/`](https://github.com/ProfDrewHall/Biocoin/tree/f723798118bb4f4d152acadf828b9ed18f3ca884/firmware), [`software/`](https://github.com/ProfDrewHall/Biocoin/tree/f723798118bb4f4d152acadf828b9ed18f3ca884/software) |

### License and evidence boundary

The inspected [root licensing notice](https://github.com/ProfDrewHall/Biocoin/blob/f723798118bb4f4d152acadf828b9ed18f3ca884/LICENSE)
and README assign **MIT** to `firmware/` and `software/`, and
**CERN-OHL-W v2.0** to `PCB/` and `fixtures/`, unless a more specific file notice
applies. Keep upstream attribution and the relevant license obligations with any
copied or derived assets. The top-level file is a license notice referencing the
license texts; it is not a full copy of both licenses.

The paper's estimated months of battery life describes particular platform
measurement and BLE settings. It is not a demonstrated months-long sensor lifetime,
clinical glucose accuracy result, or guarantee for a modified firmware workload.
Our electrode materials, coating, calibration, drift, interference, manufacturing
yield, packaging and in-vivo performance remain to be established.

### Verified electrode connector and proposed coupon connection

On wearable schematic page 1, **J5 is Molex 5034802000**. Both assembly BOM variants
list the same part. The [Molex part page](https://www.molex.com/en-us/products/part-detail/5034802000)
identifies 20 circuits, 0.50 mm pitch, right-angle surface mounting, dual contacts,
and a back-flip actuator. The [manufacturer's series guide](https://www.molex.com/content/dam/molex/molex-dot-com/en_us/pdf/product-reference-guides/987652-0257.pdf)
specifies a 0.30 mm FFC/FPC mating thickness. A thinner flex therefore needs the
correct termination stiffener. Confirm the manufacturer's drawing, contact side,
pin-1 orientation, insertion length and tolerance before releasing cartridge CAD.

| J5 contact | Schematic net | J5 contact | Schematic net |
| --- | --- | --- | --- |
| 1 | No connection | 11 | PH0 |
| 2 | AIN3 | 12 | PH1 |
| 3 | AIN2 | 13 | IONTOPH_E2 |
| 4 | AIN1 | 14 | WE1 |
| 5 | PH3 | 15 | IONTOPH_E1 |
| 6 | PH2 | 16 | WE3 |
| 7 | RE0 | 17 | TEMP- |
| 8 | CE0 | 18 | TEMP+ |
| 9 | WE2 | 19 | STRAIN- |
| 10 | WE4 | 20 | STRAIN+ |

For a first three-electrode **bench coupon**, connect working electrode to
**J5-14 / WE1**, reference to **J5-7 / RE0**, and counter to **J5-8 / CE0**. Leave
the other contacts unconnected. This is a proposed connection derived from the
upstream schematic, not a tested cartridge. There is **no ground contact on J5**;
RE0 is the electrochemical reference input and must not be replaced by digital
ground. The shield tabs are shown unconnected in this schematic.

WE1 reaches AD5940 SE0 through the TMUX1104's S1-to-D path. Upstream
[`firmware/src/drivers/ad5940_hal.cpp`](https://github.com/ProfDrewHall/Biocoin/blob/f723798118bb4f4d152acadf828b9ed18f3ca884/firmware/src/drivers/ad5940_hal.cpp)
maps software channel 0 to WE1, with MUX enable high and A1/A0 low. Its channel
map is 0 -> WE1, 1 -> WE2, 2 -> WE3, 3 -> WE4; the physical mux binary order is
different. Record both in any adapter driver. Verify continuity on an unpowered
assembled board before applying a cell bias.

The part page lists ten mating cycles maximum. For repeated bench coupon swaps,
consider a fixed flex adapter and a replaceable lab connector rather than assuming
the wearable ZIF is a high-cycle laboratory connector.

### Layer stack: resolve before fabrication

The paper describes a 6-layer, 530 mm2 FR4 board, nominally 26 mm diameter and
0.8 mm thick, with ENIG finish. The actual v1.3 Gerber `.EXTREP` maps the copper
files in order as:

| Order | Gerber | Layer name |
| --- | --- | --- |
| 1 | `.GTL` | Top Signal |
| 2 | `.G1` | GND1 |
| 3 | `.G2` | Middle Signal |
| 4 | `.G3` | Power |
| 5 | `.G4` | GND2 |
| 6 | `.GBL` | Bottom Signal |

An independent read of the embedded layer-stack fields in
`design/Biocoin_v1.3.PcbDoc` found six copper layers of 1.378 mil each
(approximately 35 um), separated by 4.3307 / 7.874 / 4.3307 / 7.874 / 4.3307 mil
dielectrics (approximately 0.11 / 0.20 / 0.11 / 0.20 / 0.11 mm). Those values add
to approximately **0.94 mm before solder mask**, or 0.96 mm including the two
0.4 mil mask entries. This conflicts with the paper's 0.8 mm description.

Do not silently choose one thickness or alter the stack to fit an enclosure.
Have the fabricator reconcile the pinned layout, exports, finish and intended
stack; keep the approved stackup with the resulting fabrication revision.

### Power, battery and assembly variants

Wearable schematic page 3 shows J1 as **BM02B-ACHSS-GAN-TF(LF)(SN)**, with contact
1 = VBAT positive and contact 2/shield tabs = GND. This is not a generic JST-PH
battery connector. The source note intends a **RJD2430C1ST1 rechargeable Li-ion
coin cell** and assumes its lead harness is soldered during assembly. The
[manufacturer RJD datasheet](https://www.cde.com/resources/catalogs/RJD.pdf)
lists the part as 110 mAh nominal. The project's no-solder assembly goal requires
the supplier to deliver the populated board and a finished, polarity-verified
matching battery harness; it does not mean an arbitrary battery plug fits.

The coin board uses MAX17270 buck/boost rails. Choose and record one BOM variant:

| Population | AVDD 3.0 V BOM | AVDD 3.6 V BOM |
| --- | --- | --- |
| R14 | 133 kilohm, ERJ-1GNF1333C | 80.6 kilohm, RC0201FR-0780K6L |
| R6, R17 | 162 kilohm, ERJ-1GNF1623C | 113 kilohm, ERJ-1GNF1133C |
| U6 | TPS7A0230PDQNR | TPS7A2036PDQNR |

The exported schematic PDF depicts the **3.6 V** population. These are actual
part/value changes, not interchangeable spreadsheet names.

The dock's power schematic uses **MCP73831T-2ACI/OT** with a **20 kilohm PROG
resistor**. Its J2 jumper selects the auxiliary LiPo (contacts 1-2) or the coin
cell connected to Biocoin (contacts 2-3). The source explicitly prohibits
connecting both batteries at once. The coin PCB itself does not contain this
charger. Retain the dock in the bring-up package and have the supplier verify
charge configuration against the chosen cell. The small/large-battery mechanical
files are packaging alternatives, not proof that every cell matching their shape
is electrically suitable.

## Auxiliary reader hardware and firmware

These are useful historical circuit, radio and interoperability references. The
commercial sensor remains the glucose transducer in each case. Compatibility is
limited to the generation/region actually stated by the source; it must not be
inferred from the word Libre or Dexcom alone.

| Project | Actual design/source assets | Compatibility and gap | License/status observed |
| --- | --- | --- | --- |
| [Original xDrip](https://github.com/StephenBlackWasAlreadyTaken/xDrip/blob/master/hardware_setup.md) | `hardware_setup.md` wiring instructions for Pololu Wixel, HM10/HM11, charger and battery | G4-era transmitter RF received by Wixel and forwarded via BLE; no new glucose sensor | App repository GPL-3.0; linked third-party hardware needs its own notice |
| [wixel-xDrip](https://github.com/StephenBlackWasAlreadyTaken/wixel-xDrip) | `apps/dexdrip/`, `radio_registers.h`, `LICENSE.txt` | Wixel proprietary-radio receiver and UART bridge; not G7 BLE | License file exists; exact text not verified in the web pass |
| [xBridge2](https://github.com/jstevensog/wixel-sdk) | `apps/xBridge2/`, root `xBridge2.pdf`, `LICENSE.txt` | G4-era Wixel -> HM10/11/16/17 BLE, battery and sleep control | Public circuit/firmware archive; exact license text not verified |
| [Parakeet](https://github.com/jamorham/wixel-xDrip) | Wixel firmware, `webservice/`, build instructions | G4-era RF -> cellular/server; historical component supply | Public source with license file; exact license text not verified |
| [xDrip-ESP32](https://github.com/Gorgy70/xDrip-ESP32) | `parakit-e3-v3.lay6`, `xDrip-ESP32.ino`, `cc2500_REG.h`, five enclosure STL files | Separate CC2500 radio + ESP32, implementing G4-era bridge functions; **not direct G5/G6/G7 BLE** | No explicit root license surfaced; obtain permission before copying assets |
| [LimiTTer](https://github.com/JoernL/LimiTTer) | `LimiTTer.pdf`, `LimiTTer.ino`, `case-3dprint/` | Original Libre ISO15693 NFC -> BM019/CR95HF -> Arduino -> HM11 BLE | No explicit license surfaced; historical build/reference material |
| [LBridge](https://github.com/keencave/LBridge) | `LBridge_Arduino_V09/`, `LBridge_Arduino_V11/`, `LBridge_RFduino_V09/`, `technical docs/` | Firmware for LimiTTer hardware; xBridge2 packet protocol to xDrip+ | MIT firmware; hardware remains separately sourced |
| [LibreMonitor](https://github.com/UPetersen/LibreMonitor) | README wiring diagram, `LibreMonitor.ino`, `LibreMonitorRFduino.ino`, iOS project | Original Libre NFC -> BM019 + Simblee/RFduino BLE; later MiaoMiao client | Apache-2.0; original hardware support stopped in 2018 |
| [Moonstone](https://github.com/paperflake/moonstone) | `Moonstone_Gerber.Zip`, `BOM.txt`, `BM019_schematics.PNG`, `limitter_skema.png`, CircuitMaker link | CR95HF + nRF52832 proposed Libre bridge; README still lists assembly, firmware port and validation as future work | No explicit license surfaced; manufacturing exports are not proof of a working device |
| [2025 HardwareX Libre converter](https://doi.org/10.1016/j.ohx.2025.e00684) | Paper Figure 8 electronics schematic; ESP32 and CR95HF architecture | Existing Libre NFC -> BLE every five minutes; 37 participants; reported MARD compares with the isCGM monitor, not laboratory blood reference | Public paper; a separately licensed, complete editable fabrication package was not verified here |
| [Dexcom-ESP32-Reader](https://github.com/TheEpicBigBoss/Dexcom-ESP32-Reader) | `ESP32_Reader/`, `ESP32_G6_Emulator/`, `Thesis.pdf` | Actual direct G5/G6 BLE firmware; experimental; README pins old Arduino ESP32 1.0.4 | Apache-2.0; no custom sensor/PCB manufacture |
| [ESPHome Dexcom](https://github.com/Fabian-Schmidt/esphome-dexcom) | `components/dexcom_ble_client/`, `example.yaml`, `example-idf.yaml` | Direct G5/G6 BLE on ESP32; no demonstrated G7 support | GPL-3.0 |

## Companion software, BLE and commercial bridges

| Source | What can be reused or studied | Boundary |
| --- | --- | --- |
| [xDrip+](https://github.com/NightscoutFoundation/xDrip) | GPL-3.0 Android collectors, calibration/logging/UI and transport implementations | Sensor support is generation/version dependent. [Current G7/ONE+/Stelo instructions](https://navid200.github.io/xDrip/docs/Dexcom/G7.html) require at least release 2026.06.17; G5/G6 ESP32 code is not a G7 implementation |
| [Juggluco](https://github.com/j-kaltes/Juggluco) | GPL-3.0 Android BLE/NFC application; current README lists Libre 2/2+/3/3+ and G7/ONE+ among supported sensors | BUILD requires algorithm/encryption `.so` libraries from an APK. The published source alone does not reproduce every dependency |
| [DiaBLE](https://github.com/gui-dos/DiaBLE) | MIT Swift NFC/BLE sensor/protocol research | Archived 2026-08-07. [G7 authentication discussion](https://github.com/gui-dos/DiaBLE/discussions/17) distinguishes authentication/parallel-app modes; do not assume standalone collection works for every sensor |
| [LoopKit LibreTransmitter](https://github.com/LoopKit/LibreTransmitter) | BLE/bridge client code; current upstream of dabear's retired project | README tests US Libre1 10-day/international Libre1, marks US Libre1 14-day untested, supports EU Libre2, excludes US Libre2 and Libre3. Review its current included license notices before reuse |
| [blueReader client](https://github.com/SandraK82/libBlueReader-iOS) | MIT iOS library for the blueReader NFC-to-BLE device | Client example/source only; no verified licensed blueReader manufacturing package found |
| [Bubble Swift client](https://github.com/bubbledevteam/bubble-client-swift) | MIT Swift client/plugin source | Not Bubble electronics/firmware manufacturing files |
| [MiaoMiao legacy client](https://github.com/dabear/miaomiao-client-swift) | Historical client pointers, now superseded by LibreTransmitter | Not MiaoMiao hardware schematics; current branch says it is abandoned |
| [Nightscout](https://github.com/nightscout/cgm-remote-monitor) | AGPL-3.0-or-later optional data server, APIs and remote display | An application/data system, not the sensor or its medical validation |
| [CYGM](https://github.com/decibelkaos/CYGM) | MIT ESP32 display firmware for JC2432W328C capacitive touchscreen board | Wi-Fi **cloud secondary display** using Dexcom Share, LibreLinkUp or Nightscout; not direct sensor BLE |

No separate credible primary project named **LibreLimiTTer** was established in
this pass; LimiTTer and LBridge are the verified projects. No licensed editable
MiaoMiao or Bubble sensor-reader manufacturing package was established either.
This records a search gap, not proof that none exists.

## Manufacturer references and own-sensor research gaps

- [ADI AD5940/AD5941](https://www.analog.com/en/products/ad5940.html) and
  [AN-1563](https://www.analog.com/en/resources/app-notes/an-1563.html) are useful
  AFE datasheet/application guidance. They do not supply glucose chemistry or
  establish clinical accuracy.
- [TI TIDA-010300](https://www.ti.com/tool/TIDA-010300), dated 2025-12-19, describes
  a sub-20 mm CGM electronics architecture. The verified public download was the
  three-page `TIDUFG7` overview; full editable schematics, named AFE and BOM were
  not established. [TI's resource terms](https://www.ti.com/legal/important-notice-and-disclaimer.html)
  are not an open hardware license. Use it as a reference, not a relicensable
  manufacturing package.
- [Uppsala's 2025 thesis](https://uu.diva-portal.org/smash/get/diva2:1980846/FULLTEXT01.pdf),
  *Design of open-source glucose sensor for continuous glucose monitoring*, is
  an own-sensor microneedle concept. Its stated scope excludes making a physical
  prototype or conducting in-vitro testing. It is not evidence that a complete
  open sensor already works.

For this project the remaining distinctive deliverable is the reproducible
electrode/cartridge process: substrate and geometry, conductive layers,
functionalization, diffusion/interference membranes, connector termination,
lot controls, raw current data, calibration and independent repeatability. A
working BLE reader, a finished PCB assembly and a responsive glucose electrode
are separate verification milestones.
