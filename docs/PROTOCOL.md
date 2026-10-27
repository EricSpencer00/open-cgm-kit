# OCK framed sensor protocol, version 1

One 20-byte frame, little-endian, shared by the strip rig (`firmware/strip-rig`), the
patched Biocoin (`firmware/biocoin-patches`) and the host (`software/bridge/ock_protocol.py`).
Encoder: `firmware/common/ock_frame.h`. Frames are exactly 20 bytes so one frame fits one
default-MTU BLE notification (ATT payload 23 - 3). They are also self-delimiting, so the host
can reassemble them from a byte stream that the Biocoin TX path chunks arbitrarily.

## Common header

| Offset | Size | Field | Value |
| --- | --- | --- | --- |
| 0 | 1 | sync | `0xA5` |
| 1 | 1 | version | `1` |
| 2 | 1 | length | total frame length including CRC, `20` |
| 3 | 1 | kind | `1` sample, `2` identity |
| 4 | 1 | status | bits 0-5 flags, bits 6-7 identity epoch |
| 18 | 2 | crc | CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) over bytes 0-17 |

## Sample frame (kind 1)

| Offset | Size | Field | Notes |
| --- | --- | --- | --- |
| 5 | 1 | reserved | 0 |
| 6 | 2 | seq | u16, +1 per sample, wraps; a jump is lost samples |
| 8 | 4 | t_ms | u32 device acquisition time, ms since boot, wraps at 49.7 days |
| 12 | 4 | current_pa | i32 electrode current in picoamps (+/-2.1 mA range), oxidation positive |
| 16 | 2 | temp_cc | i16 hundredths of a degree C; `-32768` = no measurement |

## Identity frame (kind 2)

Sent at START, every 256 samples, and (strip rig) readable on the IDENT characteristic.

| Offset | Size | Field | Notes |
| --- | --- | --- | --- |
| 5 | 1 | technique | 1 = chronoamperometry |
| 6 | 2 | rtia_x10 | u16 feedback resistance in units of 10 ohm |
| 8 | 2 | bias_mv | i16 WE-RE bias actually applied (quantized by the AFE) |
| 10 | 2 | period_ms | u16 nominal sample period |
| 12 | 4 | sensor_id | u32 strip lot / serial, 0 = unknown; supplied by the host at configuration |
| 16 | 2 | cal_id | u16 calibration identity, 0 = none; supplied by the host at configuration |

## Status byte

| Bits | Name | Meaning |
| --- | --- | --- |
| 0 | OVERRANGE | ADC or TIA output at a rail; current is only a bound |
| 1 | TEMP_INVALID | `temp_cc` is not a measurement |
| 2 | TEMP_DIE | temperature is a chip die (nRF52840 or LMP91000), not the strip |
| 3 | SETTLING | bias was applied less than a fixed settle time ago (placeholder: 30 s strip rig, 5 s Biocoin) |
| 4 | DROPPED | reserved for devices that know they dropped samples; hosts must rely on `seq` |
| 5 | reserved | 0 |
| 6-7 | epoch | increments (mod 4) whenever sensor_id, cal_id or configuration changes |

A sample belongs to the identity frame with the same epoch. The host leaves strip lot and
calibration id blank when the latest identity epoch differs, and never offers a calibration
to the Resilient core in that case.

## Host rules

- Sync, version and length are checked before the CRC. Version mismatch, bad CRC, truncated
  tail and sequence regression are each reported as distinct faults; bad frames never become samples.
- After a bad frame the host drops one byte and scans for the next valid frame, so a lost
  byte costs only the damaged frame. `seq` then reports the loss.
- Timestamps are device time. Host receipt time is logged separately; clocks are not synchronized.
- Glucose is produced only when the identity's calibration id matches a lab calibration file
  (and strip lot, if the file pins one), temperature is valid and flags are clean.

## GATT layout (both devices)

Service `00001523-1212-efde-1523-785feabc93aa`.

| Characteristic | UUID | Access | Payload |
| --- | --- | --- | --- |
| Status | `...1524` | read, notify | 1 byte: 0 stopped, 1 invalid parameters, 2 running, 3 error |
| Control | `...1528` | write | `0x01` START, `0xFF` STOP |
| Data | `...1529` | notify | OCK frames |
| Config | `...152a` | write | strip rig `<BBhHIH` (version 1, TIA gain code 1-7, bias mV, period ms, strip lot, cal id); patched Biocoin: technique byte + 17-byte CA parameters + `<HIH` (RTIA kOhm, strip lot, cal id), the 17-byte legacy form is still accepted |
| Ident | `...152b` | read | strip rig only: latest identity frame |

## Not covered

Session authentication, replay protection and encryption are not part of this protocol; BLE
pairing is not assumed to provide them. Frames are not signed. The CRC detects corruption, not tampering.
