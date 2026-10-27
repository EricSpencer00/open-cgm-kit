import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile
import unittest

import biocoin_bridge as bridge
import ock_protocol as ock

FIXTURES = Path(__file__).parent / "fixtures"


class PayloadTests(unittest.TestCase):
    def test_legacy_ca_payload_unchanged(self):
        self.assertEqual(len(bridge.ca_payload(1, 2, 10, 100, 0)), 18)

    def test_extended_ca_payload_carries_rtia_and_identity(self):
        payload = bridge.ca_payload(1, 2, 10, 100, 0, rtia_kohm=512, sensor_id=4242, cal_id=7)
        self.assertEqual(len(payload), 26)          # technique byte + 25 parameter bytes
        self.assertEqual(struct.unpack("<HIH", payload[18:]), (512, 4242, 7))

    def test_rtia_must_be_a_supported_value(self):
        for kohm in (5, 11, 513, 1000):
            with self.subTest(kohm=kohm), self.assertRaises(ValueError):
                bridge.ca_payload(1, 2, 10, 100, 0, rtia_kohm=kohm)
        for kohm in bridge.BIOCOIN_RTIA_KOHM:
            bridge.ca_payload(1, 2, 10, 100, 0, rtia_kohm=kohm)

    def test_strip_rig_payload(self):
        self.assertEqual(bridge.strip_rig_payload(7, 594, 1000, 4242, 7),
                         struct.pack("<BBhHIH", 1, 7, 594, 1000, 4242, 7))
        for args in ((0, 0, 1000), (8, 0, 1000), (7, 0, 99), (7, 0, 60001)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                bridge.strip_rig_payload(*args)


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.rz = os.environ.get("RZ_BIN") or shutil.which("rz")
        if not self.rz:
            self.skipTest("installed rz not found; set RZ_BIN")

    def run_replay(self, calibration=True):
        out = io.StringIO()
        records = []
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "log.csv"
            with open(csv_path, "w", newline="") as handle:
                cal = bridge.load_calibration(str(FIXTURES / "strip_rig_calibration.json")) if calibration else None
                sink = bridge.FramedSink(self.rz, cal, ock.CsvLog(handle))
                with contextlib.redirect_stdout(out):
                    stream = bridge.replay_capture(str(FIXTURES / "strip_rig_session.hex"), sink)
            rows = csv_path.read_text().splitlines()
        records = [json.loads(line) for line in out.getvalue().splitlines()]
        return records, rows, stream

    def test_fixture_replay_with_calibration(self):
        records, rows, stream = self.run_replay()
        samples = [r for r in records if "raw_current_pA" in r]
        self.assertEqual([(r["device_sequence"], r["status"], r["glucose_mgdl"]) for r in samples], [
            (0, "warmup", None), (1, "warmup", None), (2, "ready", 220),
            (3, "ready", 40), (4, "ready", 400), (7, "ready", 220), (9, "ready", 220)])
        self.assertEqual([r["lost_before"] for r in samples], [0, 0, 0, 0, 0, 2, 1])
        self.assertEqual(stream.stats["lost_samples"], 3)
        self.assertEqual(stream.stats["crc_failures"], 1)
        self.assertEqual(stream.stats["truncated"], 1)
        self.assertEqual({r["kind"] for r in records if r.get("status") == "frame_fault"},
                         {"crc", "truncated"})
        self.assertTrue(all(r["strip_lot"] == 4242 and r["device_calibration_id"] == 7 for r in samples))
        self.assertEqual(len(rows), 1 + len(samples))
        self.assertEqual(rows[3], f"3000,{rows[3].split(',')[1]},2,5000,37000,0x44,4242,7,0")

    def test_no_glucose_without_calibration(self):
        records, _, _ = self.run_replay(calibration=False)
        samples = [r for r in records if "raw_current_pA" in r]
        self.assertEqual(len(samples), 7)
        self.assertTrue(all(r["glucose_mgdl"] is None for r in samples))
        self.assertEqual({r["status"] for r in samples}, {"warmup", "uncalibrated"})

    def test_calibration_for_another_id_or_lot_is_not_applied(self):
        base = json.loads((FIXTURES / "strip_rig_calibration.json").read_text())
        for change in ({"id": 8}, {"strip_lot": 1}):
            with self.subTest(change=change):
                cal = {**base, **change}
                ident = ock.Ident(0x40, 1, 350000, 594, 1000, 4242, 7)
                reading = ock.Reading(ock.Sample(0x44, 3, 4000, 5000, 3700), 3, 4000, 0, ident)
                result = bridge.evaluate_reading(reading, cal, self.rz)
                self.assertIsNone(result["glucose_mgdl"])
                self.assertIsNone(result["calibration_id"])

    def test_missing_identity_or_temperature_blocks_glucose(self):
        cal = json.loads((FIXTURES / "strip_rig_calibration.json").read_text())
        ident = ock.Ident(0x40, 1, 350000, 594, 1000, 4242, 7)
        no_ident = ock.Reading(ock.Sample(0x44, 3, 4000, 5000, 3700), 3, 4000, 0, None)
        self.assertIsNone(bridge.evaluate_reading(no_ident, cal, self.rz)["glucose_mgdl"])
        no_temp = ock.Reading(ock.Sample(0x46, 3, 4000, 5000, ock.TEMP_INVALID), 3, 4000, 0, ident)
        result = bridge.evaluate_reading(no_temp, cal, self.rz)
        self.assertEqual((result["status"], result["glucose_mgdl"]), ("invalid_sample", None))
        over = ock.Reading(ock.Sample(0x45, 3, 4000, 5000, 3700), 3, 4000, 0, ident)
        self.assertEqual(bridge.evaluate_reading(over, cal, self.rz)["status"], "sensor_fault")

    def test_calibration_file_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cal.json"
            path.write_text(json.dumps({"enabled": True}))
            with self.assertRaises(ValueError):
                bridge.load_calibration(str(path))


if __name__ == "__main__":
    unittest.main()
