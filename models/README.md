# Electrode model

Dry-lab model of the GOx amperometric glucose electrode: 1D reaction-diffusion
through the layer stack (electrode | enzyme | outer membrane | boundary layer),
ping-pong GOx kinetics in glucose and oxygen, H2O2 collection at the electrode,
acetaminophen as an electroactive interferent, and the Biocoin AD5940 readout
quantization as configured in the pinned firmware.

```sh
python3 models/electrode_model.py            # presets -> models/out/
python3 models/electrode_model.py --mc 200   # + Monte Carlo sensitivity (~4 min)
cd models && python3 -m unittest -v
```

Needs numpy, scipy, matplotlib.

## What it verifies

The tests check the solver against closed-form limits: series diffusion of
peroxide and acetaminophen (to 0.1%), the glucose-flux-limited regime with
peroxide split by layer resistance (to 3%), mass conservation, grid
convergence, partition versus diffusivity behaviour, and the firmware's
code-to-current formula.

## What it found

![model](out/model.png)

| Finding | Consequence |
| --- | --- |
| The outer membrane's glucose permeability drives sensitivity and tissue linearity (Spearman ±0.85–0.89). Enzyme loading and Km barely matter while the membrane limits flux. | Spend the effort on the membrane. Sloppy home enzyme loading is tolerable. |
| A membrane that is linear to 30 mM in an air-saturated beaker saturates near 3 mM at tissue oxygen (0.06 mM). | Beaker tests must include low-O2 runs (N2-sparged to ~0.05 mM), otherwise they pass sensors that fail on the body. |
| Linearity at tissue O2 needs O2:glucose permeability of roughly 600 or more, leaving ~3–4 nA/mM on the 1.2 mm A0 disk. | Target spec for the membrane, and the measurement that qualifies it. |
| At 3–4 nA/mM the firmware's 10 kΩ CA gain resolves ~1 mM per ADC count. 160 kΩ gives 0.06 mM; 512 kΩ gives 0.02 mM and still fits 25 mM. | Raise `LptiaRtiaSel` in `echem_ca.cpp` before wet tests with a tissue-grade membrane. |
| Acetaminophen error scales almost entirely with the membrane's acetaminophen:glucose permeability ratio (Spearman 0.98). A Prussian-blue electrode at ~0 V removes it in the model. | Prussian-blue screen-printed electrodes are the cheapest interference fix. |
| A 4 mm commercial screen-printed electrode gives ~11× the current of the A0 disk. | Use commercial strips for the first wet runs; 80 kΩ fits them. |

`out/report.json` holds every number above. `out/synthetic_trace_gox_pu.csv` is
a 24 h raw-current trace (meals, interstitial-fluid lag, drift, noise, ADC
quantization) for exercising the calibration software.

## What it cannot tell you

The membrane permeabilities, enzyme retention, Ag/AgCl reference stability,
fouling, enzyme loss and sensitivity drift over days, and anything about tissue
response. The presets use literature-range guesses. A 1D model also ignores
edge diffusion at the disk rim, a few percent for 15 µm films on a 1.2 mm disk.
The fastest way to make the model predictive is to fit the three membrane
permeabilities (glucose, O2, acetaminophen) from a handful of bench
measurements: a calibration curve at two O2 levels plus one acetaminophen spike.
