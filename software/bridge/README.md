# Biocoin bench bridge

This adapter receives real chronoamperometry (CA) current from upstream Biocoin firmware and invokes the Resilient core. It does not turn the upstream instrument into a validated CGM. No hardware has been connected during this implementation.

Run the complete software path without hardware or BLE dependencies:

```sh
RZ_BIN=/absolute/path/to/rz python3 software/bridge/biocoin_bridge.py --demo
RZ_BIN=/absolute/path/to/rz python3 -m unittest discover -s software/bridge -v
```

The demo explicitly marks its bytes, calibration and resulting concentration as synthetic. Integration tests execute the actual `.rz` core rather than reimplementing its calibration in Python. The adapter passes only validated primitive integers and booleans into generated `.rz` source and invokes `rz` without a shell.

## Live bench acquisition

Install the BLE dependency in your project environment with `python3 -m pip install -r software/bridge/requirements.txt`. Use a Biocoin flashed with the pinned upstream firmware, a wired three-electrode bench cell, and reference solutions. Use the operating system's BLE device address/identifier for that specific instrument.

BLE mode requires an explicit address, sampling interval, processing interval, upstream current hint, electrode bias and channel. Choose these from the electrode's characterization and actual wiring; the bridge intentionally supplies no electrochemical defaults. The `--max-current-ua` option follows the upstream Python SDK's naming, but pinned CA firmware labels that field as an mA hint and does not apply it to the AFE: its RTIA selection remains fixed at 10 kΩ. This option provides no hardware current limit or automatic range selection. Resolve the upstream unit discrepancy and characterize the actual AFE response before using the parameter experimentally. For example, the invocation shape is:

```text
python3 software/bridge/biocoin_bridge.py --address DEVICE_IDENTIFIER --sampling-s SECONDS --processing-s SECONDS --max-current-ua MICROAMPS --bias-mv MILLIVOLTS --channel CHANNEL --duration-s SECONDS
```

This command refuses a device that is not idle, then configures the device, starts CA, records JSON lines to standard output, and sends STOP on exit while connected only if this bridge attempted START. It validates the service, configuration status and running status, subscribes before START, reassembles fragmented little-endian float32 data, rejects non-finite/out-of-bounds currents and ends logging on queue overflow or disconnect. After STOP it checks status and drains notifications until a 250 ms quiet window or a two-second bound. The ending record always says `capture_complete: false`: the upstream stream has no sequence or end marker, so this bounded drain cannot establish lossless capture. Notification cleanup still runs when STOP fails. Channel indexes are `0..3`, matching upstream validation. Electrode bias must also satisfy the firmware's narrower Vzero-dependent limits; a rejected configuration must be corrected rather than retried unchanged.

The pinned firmware's BLE disconnect callback stops battery monitoring but does not stop CA acquisition. A lost link therefore does not guarantee that electrode bias or acquisition has stopped. The bridge reports inability to confirm STOP; recover instrument control with the upstream software and confirm a stopped status before another run. This bridge does not replace an instrument-side disconnect watchdog.

Live results contain measured `raw_current_pA` and `glucose_mgdl: null`. The CA stream carries **no acquisition timestamp, device sequence or concurrent temperature**. The bridge reports host receipt age separately, does not invent missing observations, and keeps glucose unavailable through the Resilient guards. Upstream also documents possible TX byte drops. Float reassembly can handle fragmentation, but cannot reliably detect lost bytes or prove sample freshness. A complete CGM transport needs timestamped, framed, versioned samples with sequence, technique identity, temperature and integrity checks, plus characterized batching latency. This bridge is useful for bench current logging before that firmware work.

Source alignment: upstream `software/src/biocoin/device.py`, `techniques/ca.py`, `techniques/base_technique.py`, and `firmware/docs/BLE_PROTOCOL.md`. CA config is an 18-byte `<BffffB` packet including the technique ID; the parameter struct itself is 17 bytes. Data floats are current in µA, converted to integer pA. Status values are 0 stopped, 1 invalid parameters, 2 running, 3 error, 4 current limit exceeded. The firmware's acquisition-running state does not establish that sensor chemistry is stable.
