# Open CGM Kit

What if you could vibe code / CAD / wet-lab a CGM? 

----------

An open glucose sensor: our own electrode, open readout electronics, and
calibration software.

**Status:** designed and software-tested. No sensor has been fabricated or has
measured glucose. Not for human use or treatment decisions.

## Path to an MVP

1. **Strip rig.** Commercial glucometer strips + LMP91000 front end + ESP32 BLE
   → calibration software. Proves the readout, firmware and calibration end to
   end without chemistry.
2. **Coated electrodes.** Contract-coated GOx electrodes built to the membrane
   spec from the model. Bench tests at air and low O2.
3. **Biocoin readout.** Port to the open UCSD [Biocoin](https://github.com/ProfDrewHall/Biocoin) board with CA gain raised
   from 10 kΩ to ≥160 kΩ.
4. **Wearable sensor.** Separate future development.

## Run

```sh
python3 models/electrode_model.py                     # electrode model -> models/out/
cd models && python3 -m unittest -v                   # model verification
RZ_BIN=/path/to/rz sh software/resilient/run_checks.sh   # calibration core
RZ_BIN=/path/to/rz python3 -m unittest discover -s software/bridge -v
```

## Layout

| Path | Contents |
| --- | --- |
| `models/` | Electrode reaction-diffusion model, membrane spec, readout resolution |
| `software/` | Resilient calibration core and Biocoin BLE bridge |
| `hardware/`, `mechanical/` | A0 electrode masks, enclosure and pad CAD |
| `vendor/biocoin/` | Upstream [Biocoin](https://github.com/ProfDrewHall/Biocoin) readout (PCB, firmware, host), pinned and hashed |
| `docs/A0_PACKAGE.md` | Full A0 package: contents, delivered box, Bluetooth, provenance |
| `docs/SENSOR_PROCESS.md` | Sensor chemistry, layer stack, bench test gates |
| `docs/RELEASE_STATUS.md` | What is verified and what remains |
| `docs/FABRICATION.md`, `docs/COST_AND_BOX.md` | Supplier handoff and cost |
| `docs/OPEN_HARDWARE_CATALOG.md` | Survey of open CGM hardware and software |

## License

Hardware CERN-OHL-W-2.0, software MIT, docs CC-BY-4.0. Biocoin keeps its
upstream licenses. See `LICENSES/` and `docs/ATTRIBUTION.md`.
