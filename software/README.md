# Software

The first implementation is a [Resilient calibration core](resilient/README.md) with labeled synthetic fixtures and a [Biocoin BLE bench bridge](bridge/README.md). The core evaluates raw electrode current against a supplied lab calibration and prevents uncalibrated, warming, faulty, stale or out-of-envelope samples from exposing a glucose value.

The acquisition boundary is explicit: the hardware layer must deliver signed current in pA, temperature in milli-degrees Celsius, sample age, sequence and sensor state. The core returns status, optional integer glucose in mg/dL and calibration identity. A companion app can consume those fields and convert display units locally.

The bridge implements upstream Biocoin CA configuration and BLE current logging. Upstream's unframed current stream omits acquisition timestamps, device sequence and simultaneous temperature, so live glucose stays unavailable. The bridge's synthetic demo exercises byte parsing through the actual Resilient core.

Authenticated framing, session replay protection, the companion app and Resilient device deployment remain separate implementation work. The current `.rz` files run on the host CLI; they are not a flashable BLE firmware release. All provided demo values and coefficients are synthetic, and no clinical accuracy or dosing use is established.
