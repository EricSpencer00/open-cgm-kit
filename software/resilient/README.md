# Resilient calibration core

This is executable host-side `.rz` source for the sensor R&D pipeline. It turns bounded electrode current into an explicitly qualified result using a supplied two-point laboratory calibration. The fixtures contain invented currents and coefficients. They demonstrate software behavior, not a working glucose sensor or clinical accuracy.

Run with an installed Resilient CLI:

```sh
RZ_BIN=/absolute/path/to/rz sh software/resilient/run_checks.sh
```

`glucose_core.rz` contains the domain code. `synthetic_fixtures.rz` supplies test inputs. `core_tests.rz` exercises accepted values and rejected states; `demo.rz` prints labeled synthetic output. The check script does not download or build a compiler.

## Inputs and results

`SensorSample` holds a uint32-range sequence number, signed current in pA, temperature in milli-degrees Celsius, sample age in milliseconds, and state: `0` offline, `1` warming up, `2` ready, `3` sensor fault. A transport must supply measured current, temperature and truthful acquisition state; sending `2` is not evidence that chemistry has stabilized.

`Calibration` stores the currents observed at two increasing glucose reference concentrations, an allowed temperature interval, and an identifier. Either current polarity is supported. Enable it only after the lab's release process accepts the fitted response. Preserve the underlying measurements, fabrication lot, reference method, timestamp and calibration version outside this small core. The numeric identifier alone does not establish traceability.

`evaluate` returns a status plus `has_glucose`. A number is present only for a ready sensor, enabled valid calibration, fresh sample, current inside the calibration interval and temperature inside its validated interval. All rejected states return `has_glucose=false`, `glucose_mgdl=-1` and `calibration_id=0`; never display the sentinel as a reading. Interpolation uses bounded signed integer arithmetic and rounds to the nearest whole mg/dL. `mmol_l_tenths` provides optional one-decimal display conversion.

The accepted numerical limits are software bounds, not physiological or clinical claims: current ±1e9 pA, calibration concentrations 1–1000 mg/dL, instrument temperature −40–85 °C, maximum configured sample age 1–3,600,000 ms. The synthetic fixture uses a 35–39 °C calibration interval and a 300,000 ms age policy only to test the guards. Real limits must come from experiments.

## Receiver freshness contract

Call `effective_age_ms(packet_age_ms, received_monotonic_ms, now_monotonic_ms, max_age_ms)` before evaluation/display, and reevaluate as time passes. It returns `-1` for invalid clock inputs or an age above the limit for stale data. Keep receipt and current times from the same monotonic clock. A clock/session reset invalidates cached data. Packet timestamps are untrusted until the transport checks them. The transport must also reject duplicate/out-of-order sequence numbers per sensor session and clear cached results on disconnect; that session state is outside this pure core.

## What still needs research and implementation

Two-point interpolation assumes a stable, linear response inside its interval. This code does not establish selectivity, temperature compensation, oxygen dependence, tissue lag, drift, calibration expiry, sensor wear life, sterility, biocompatibility or medical safety. It does not compensate for those effects. Until data supports a more complete model, glucose output is a bench estimate. Use held-out reference solutions across the interval to measure nonlinearity and drift rather than validating against the two fit points alone.

No BLE radio driver, secure pairing, packet authentication, ADC/AFE driver or microcontroller firmware image is included. Resilient's inspected `docs/no-std.md` describes a portable embedded value runtime; the embedded program evaluator is still future work and the Cortex-M demo is a build check. Running this source with `rz` verifies host behavior. It does not demonstrate MCU deployment, formal proof discharge or medical-device qualification. Contracts are checked by the available runtime; no Z3 certificate is claimed.
