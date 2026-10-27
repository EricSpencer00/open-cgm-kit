"""Regenerate fixtures/strip_rig_session.hex (run from software/bridge). Frames match the C encoder."""
import json
import sys

sys.path.insert(0, ".")
import ock_protocol as ock

lines = ["# strip rig session: ident, 2 settling samples, 3 good, gap of 2, corrupt frame, split frame, trailing junk"]
ident = ock.encode_ident(350000, 594, 1000, 4242, 7, epoch=1)
lines.append(ident.hex() + "  # ident: 350k, 594 mV, 1 s, strip lot 4242, cal 7")


def sample(seq, t, pa, status=0):
    return ock.encode_sample(seq, t, pa, 3700, status | ock.ST_TEMP_DIE, epoch=1)


frames = [sample(0, 1000, 5000, ock.ST_SETTLING), sample(1, 2000, 5000, ock.ST_SETTLING),
          sample(2, 3000, 5000), sample(3, 4000, 1000), sample(4, 5000, 9000),
          sample(7, 8000, 5000)]                      # seq 5 and 6 never arrived
for frame in frames:
    lines.append(frame.hex())
bad = bytearray(sample(8, 9000, 5000))
bad[13] ^= 0x40                                       # flipped bit, CRC must fail
lines.append(bytes(bad).hex() + "  # corrupt")
tail = sample(9, 10000, 5000)
lines.append(tail[:7].hex() + "  # split across two notifications")
lines.append(tail[7:].hex())
lines.append("a501")                                  # truncated trailer
open("fixtures/strip_rig_session.hex", "w").write("\n".join(lines) + "\n")
json.dump({"enabled": True, "id": 7, "low_current_pa": 1000, "high_current_pa": 9000,
           "low_glucose_mgdl": 40, "high_glucose_mgdl": 400, "min_temp_mc": 35000,
           "max_temp_mc": 39000, "strip_lot": 4242}, open("fixtures/strip_rig_calibration.json", "w"), indent=2)
open("fixtures/strip_rig_calibration.json", "a").write("\n")
