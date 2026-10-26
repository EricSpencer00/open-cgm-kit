import argparse
import asyncio
import math
import os
import shutil
import struct
import types
import unittest
from unittest.mock import patch

from biocoin_bridge import (
    CONFIG_UUID, CONTROL_UUID, SERVICE_UUID, CurrentStream, SAMPLE_FIELDS,
    ca_payload, parse_status, receive, run_core, rz_struct, synthetic_calibration,
)


class ParserTests(unittest.TestCase):
    def test_split_and_coalesced_notifications(self):
        stream = CurrentStream()
        payload = struct.pack("<fff", 0.0016, -0.002, 1.0)
        self.assertEqual(stream.feed(payload[:3]), [])
        self.assertEqual(stream.feed(payload[3:7]), [1600])
        self.assertEqual(stream.feed(payload[7:]), [-2000, 1000000])
        stream.finish()

    def test_nonfinite_samples(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                CurrentStream().feed(struct.pack("<f", value))

    def test_current_bounds(self):
        self.assertEqual(CurrentStream().feed(struct.pack("<f", -1000.0)), [-1000000000])
        with self.assertRaises(ValueError):
            CurrentStream().feed(struct.pack("<f", 1000.5))

    def test_truncated_stream(self):
        stream = CurrentStream()
        stream.feed(b"\x00\x00")
        with self.assertRaises(ValueError):
            stream.finish()

    def test_status_exact_length(self):
        self.assertEqual(parse_status(b"\x02"), 2)
        for payload in (b"", b"\x02\x00", b"\x05"):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                parse_status(payload)

    def test_ca_wire_layout(self):
        self.assertEqual(ca_payload(1, 2, 10, 100, 0), struct.pack("<BffffB", 1, 1, 2, 10, 100, 0))
        self.assertEqual(len(ca_payload(1, 2, 10, 100, 0)), 18)

    def test_invalid_ca_parameters(self):
        for args in ((math.nan, 2, 10, 0, 0), (2, 1, 10, 0, 0), (1, 2, 1001, 0, 0),
                     (1, 2, 10, 1001, 0), (1, 2, 10, 0, 4)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                ca_payload(*args)

    def test_codegen_rejects_nonintegers_and_extra_fields(self):
        sample = dict(zip(SAMPLE_FIELDS, (1, 1600, 37000, 0, 2)))
        sample["sequence"] = "1; println(99);"
        with self.assertRaises(ValueError):
            rz_struct("SensorSample", SAMPLE_FIELDS, sample)
        sample["sequence"] = True
        with self.assertRaises(ValueError):
            rz_struct("SensorSample", SAMPLE_FIELDS, sample)
        sample["sequence"] = 1
        sample["extra"] = 1
        with self.assertRaises(ValueError):
            rz_struct("SensorSample", SAMPLE_FIELDS, sample)


class ResilientIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.rz = os.environ.get("RZ_BIN") or shutil.which("rz")
        if not self.rz:
            self.skipTest("installed rz not found; set RZ_BIN")

    def test_synthetic_current_through_actual_resilient_core(self):
        current = CurrentStream().feed(struct.pack("<f", 0.0016))[0]
        sample = dict(zip(SAMPLE_FIELDS, (1, current, 37000, 0, 2)))
        self.assertEqual(run_core(sample, synthetic_calibration(), self.rz),
                         {"status": "ready", "glucose_mgdl": 220, "calibration_id": 1})

    def test_live_missing_observations_never_emit_glucose(self):
        sample = dict(zip(SAMPLE_FIELDS, (1, 1600, -40001, -1, 1)))
        cal = synthetic_calibration()
        cal["enabled"] = False
        cal["id"] = 0
        self.assertEqual(run_core(sample, cal, self.rz),
                         {"status": "invalid_sample", "glucose_mgdl": None, "calibration_id": None})


class FakeClient:
    def __init__(self, *, initial_status=0, reject_config=False, fail_stop=False,
                 fail_start=False, tail=False, invalid_tail=False):
        self.status = initial_status
        self.reject_config = reject_config
        self.fail_stop = fail_stop
        self.fail_start = fail_start
        self.tail = tail
        self.invalid_tail = invalid_tail
        self.is_connected = True
        self.services = [types.SimpleNamespace(uuid=SERVICE_UUID)]
        self.writes = []
        self.notifications_stopped = False
        self.callback = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        self.is_connected = False

    async def read_gatt_char(self, _uuid):
        return bytes([self.status])

    async def start_notify(self, _uuid, callback):
        self.callback = callback

    async def stop_notify(self, _uuid):
        self.notifications_stopped = True

    async def write_gatt_char(self, uuid, value, **_kwargs):
        self.writes.append((uuid, value))
        if uuid == CONFIG_UUID and self.reject_config:
            self.status = 1
        if uuid == CONTROL_UUID and value == b"\x01":
            self.status = 3 if self.fail_start else 2
        if uuid == CONTROL_UUID and value == b"\xff":
            if self.fail_stop:
                raise RuntimeError("mock STOP acknowledgement failed")
            self.status = 0
            if self.tail:
                data = struct.pack("<f", 0.0016)
                self.callback(None, data[:3])
                asyncio.get_running_loop().call_later(0.01, self.callback, None, data[3:])
            if self.invalid_tail:
                self.callback(None, struct.pack("<f", math.nan))


class AcquisitionLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def invoke(self, client, records):
        args = argparse.Namespace(sampling_s=1.0, processing_s=2.0,
                                  max_current_ua=10.0, bias_mv=100.0, channel=0,
                                  address="mock-device", duration_s=0, rz_bin="mock-rz")

        async def no_sleep(_seconds):
            pass

        with patch.dict("sys.modules", {"bleak": types.SimpleNamespace(BleakClient=lambda *_a, **_k: client)}), \
             patch("biocoin_bridge.asyncio.sleep", no_sleep), \
             patch("biocoin_bridge.emit", records.append), \
             patch("biocoin_bridge.run_core", return_value={"status": "invalid_sample", "glucose_mgdl": None, "calibration_id": None}):
            await receive(args)

    async def test_existing_run_is_untouched(self):
        client = FakeClient(initial_status=2)
        with self.assertRaisesRegex(RuntimeError, "existing run left untouched"):
            await self.invoke(client, [])
        self.assertEqual(client.writes, [])
        self.assertIsNone(client.callback)

    async def test_rejected_configuration_does_not_send_stop(self):
        client = FakeClient(reject_config=True)
        with self.assertRaisesRegex(RuntimeError, "rejected CA configuration"):
            await self.invoke(client, [])
        self.assertEqual([uuid for uuid, _value in client.writes], [CONFIG_UUID])
        self.assertTrue(client.notifications_stopped)

    async def test_fragmented_stop_tail_is_drained_without_complete_claim(self):
        client = FakeClient(tail=True)
        records = []
        await self.invoke(client, records)
        raw_records = [record for record in records if "raw_current_pA" in record]
        self.assertEqual(len(raw_records), 1)
        self.assertEqual(raw_records[0]["raw_current_pA"], 1600)
        self.assertIsNone(raw_records[0]["glucose_mgdl"])
        endings = [record for record in records if record["status"] == "capture_ended"]
        self.assertEqual(len(endings), 1)
        self.assertFalse(endings[0]["capture_complete"])
        self.assertTrue(client.notifications_stopped)
        self.assertEqual([value for uuid, value in client.writes if uuid == CONTROL_UUID], [b"\x01", b"\xff"])

    async def test_stop_failure_still_unsubscribes(self):
        client = FakeClient(fail_stop=True)
        with self.assertRaisesRegex(RuntimeError, "capture cleanup failed"):
            await self.invoke(client, [])
        self.assertTrue(client.notifications_stopped)

    async def test_corrupt_stop_tail_fails_capture(self):
        client = FakeClient(invalid_tail=True)
        records = []
        with self.assertRaisesRegex(RuntimeError, "transport failed while draining"):
            await self.invoke(client, records)
        self.assertTrue(client.notifications_stopped)
        self.assertTrue(any(record["status"] == "transport_fault" for record in records))

    async def test_cleanup_failure_preserves_original_start_error(self):
        client = FakeClient(fail_start=True, fail_stop=True)
        records = []
        with self.assertRaisesRegex(RuntimeError, "failed to start"):
            await self.invoke(client, records)
        self.assertTrue(client.notifications_stopped)
        self.assertTrue(any(record["status"] == "cleanup_fault" for record in records))


if __name__ == "__main__":
    unittest.main()
