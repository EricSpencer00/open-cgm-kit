import io
import unittest

import ock_protocol as ock

# Golden vectors shared with firmware/common/test/test_ock_frame.c.
GOLDEN_SAMPLE = "a50114014400010240e201007929edff800e31ae"
GOLDEN_IDENT = "a5011402400100c82602e803efcdab00070080a3"


def sample(seq, t=1000, pa=5000, temp=3700, status=0, epoch=0):
    return ock.encode_sample(seq, t, pa, temp, status, epoch)


class DecodeTests(unittest.TestCase):
    def test_crc_check_value(self):
        self.assertEqual(ock.crc16(b"123456789"), 0x29B1)

    def test_golden_sample_matches_c_encoder(self):
        frame = bytes.fromhex(GOLDEN_SAMPLE)
        self.assertEqual(ock.encode_sample(513, 123456, -1234567, 3712, ock.ST_TEMP_DIE, epoch=1), frame)
        decoded = ock.decode_frame(frame)
        self.assertEqual((decoded.seq, decoded.t_ms, decoded.current_pa, decoded.temp_cc, decoded.epoch),
                         (513, 123456, -1234567, 3712, 1))
        self.assertEqual(decoded.temp_mc, 37120)
        self.assertTrue(decoded.status & ock.ST_TEMP_DIE)

    def test_golden_ident_matches_c_encoder(self):
        frame = bytes.fromhex(GOLDEN_IDENT)
        self.assertEqual(ock.encode_ident(512000, 550, 1000, 0xABCDEF, 7, epoch=1), frame)
        ident = ock.decode_frame(frame)
        self.assertEqual((ident.rtia_ohm, ident.bias_mv, ident.period_ms, ident.sensor_id, ident.cal_id),
                         (512000, 550, 1000, 0xABCDEF, 7))

    def test_invalid_temperature_has_no_value(self):
        decoded = ock.decode_frame(ock.encode_sample(0, 0, 0))
        self.assertIsNone(decoded.temp_mc)
        self.assertTrue(decoded.status & ock.ST_TEMP_INVALID)

    def test_truncated_frames(self):
        frame = sample(1)
        for length in (0, 2, 3, 19):
            with self.subTest(length=length), self.assertRaises(ock.TruncatedFrame):
                ock.decode_frame(frame[:length])

    def test_crc_failure_on_any_flipped_bit(self):
        frame = sample(1)
        for index in range(4, ock.FRAME_LEN):
            bad = bytearray(frame)
            bad[index] ^= 0x01
            with self.subTest(index=index), self.assertRaises(ock.CrcError):
                ock.decode_frame(bytes(bad))

    def test_version_mismatch_is_distinct_from_crc(self):
        bad = bytearray(sample(1))
        bad[1] = 2
        bad[-2:] = ock.crc16(bytes(bad[:-2])).to_bytes(2, "little")   # valid CRC, wrong version
        with self.assertRaises(ock.VersionMismatch):
            ock.decode_frame(bytes(bad))

    def test_bad_sync_length_kind_and_trailing_bytes(self):
        frame = sample(1)
        with self.assertRaises(ock.BadFrame):
            ock.decode_frame(b"\x00" + frame[1:])
        with self.assertRaises(ock.BadFrame):
            ock.decode_frame(frame + b"\x00")
        short = bytearray(frame)
        short[2] = 12
        with self.assertRaises(ock.BadFrame):
            ock.decode_frame(bytes(short))
        unknown = bytearray(frame)
        unknown[3] = 0x7F
        unknown[-2:] = ock.crc16(bytes(unknown[:-2])).to_bytes(2, "little")
        with self.assertRaises(ock.BadFrame):
            ock.decode_frame(bytes(unknown))


class StreamTests(unittest.TestCase):
    def readings(self, items):
        return [item for item in items if isinstance(item, ock.Reading)]

    def faults(self, items):
        return [item.kind for item in items if isinstance(item, ock.Fault)]

    def test_contiguous_stream_has_no_gaps(self):
        items, stream = ock.replay([sample(n, 1000 * n) for n in range(5)])
        self.assertEqual([r.lost_before for r in self.readings(items)], [0] * 5)
        self.assertEqual(stream.stats["lost_samples"], 0)

    def test_sequence_gap_is_counted(self):
        items, stream = ock.replay([sample(1), sample(2, 2000), sample(5, 5000)])
        readings = self.readings(items)
        self.assertEqual([r.lost_before for r in readings], [0, 0, 2])
        self.assertEqual(readings[-1].seq_ext, 5)
        self.assertEqual(stream.stats["lost_samples"], 2)

    def test_sequence_and_time_wrap(self):
        items, _ = ock.replay([sample(65535, 0xFFFFFFF0), sample(0, 0x10)])
        first, second = self.readings(items)
        self.assertEqual(second.lost_before, 0)
        self.assertEqual(second.seq_ext, first.seq_ext + 1)
        self.assertEqual(second.device_time_ms - first.device_time_ms, 0x20)

    def test_duplicate_or_regressed_sequence_is_a_fault(self):
        items, stream = ock.replay([sample(3), sample(4, 2000), sample(4, 2000), sample(2, 3000)])
        self.assertEqual(len(self.readings(items)), 2)
        self.assertEqual(self.faults(items), ["sequence_regression"] * 2)

    def test_crc_failure_is_reported_and_stream_recovers(self):
        bad = bytearray(sample(2, 2000))
        bad[12] ^= 0xFF
        items, stream = ock.replay([sample(1) + bytes(bad) + sample(3, 3000)])
        self.assertEqual(self.faults(items), ["crc"])
        readings = self.readings(items)
        self.assertEqual([r.sample.seq for r in readings], [1, 3])
        self.assertEqual(readings[1].lost_before, 1)
        self.assertEqual(stream.stats["crc_failures"], 1)

    def test_dropped_byte_resynchronizes(self):
        damaged = sample(2, 2000)[:9] + sample(2, 2000)[10:]      # one byte lost mid-frame
        items, _ = ock.replay([sample(1) + damaged + sample(3, 3000) + sample(4, 4000)])
        self.assertEqual([r.sample.seq for r in self.readings(items)], [1, 3, 4])
        self.assertIn("crc", self.faults(items))

    def test_version_mismatch_reported_not_decoded(self):
        bad = bytearray(sample(1))
        bad[1] = 2
        bad[-2:] = ock.crc16(bytes(bad[:-2])).to_bytes(2, "little")
        items, stream = ock.replay([bytes(bad), sample(2, 2000)])
        self.assertEqual(self.faults(items)[0], "version_mismatch")
        self.assertEqual([r.sample.seq for r in self.readings(items)], [2])
        self.assertEqual(stream.stats["version_mismatches"], 1)

    def test_truncated_tail_reported_at_finish(self):
        items, _ = ock.replay([sample(1), sample(2, 2000)[:11]])
        self.assertEqual(self.faults(items), ["truncated"])

    def test_notification_split_across_chunks(self):
        frame = sample(1)
        items, _ = ock.replay([frame[:5], frame[5:6], frame[6:]])
        self.assertEqual(len(self.readings(items)), 1)

    def test_strict_mode_raises(self):
        stream = ock.FrameStream(strict=True)
        bad = bytearray(sample(1))
        bad[10] ^= 1
        with self.assertRaises(ock.CrcError):
            stream.feed(bytes(bad))
        stream = ock.FrameStream(strict=True)
        stream.feed(sample(1)[:10])
        with self.assertRaises(ock.TruncatedFrame):
            stream.finish()

    def test_oversized_notification_rejected(self):
        with self.assertRaises(ValueError):
            ock.FrameStream().feed(bytes(513))

    def test_identity_attached_only_when_epoch_matches(self):
        ident = ock.encode_ident(350000, 594, 1000, 4242, 7, epoch=1)
        items, _ = ock.replay([sample(0, 0, epoch=0), ident, sample(1, 1000, epoch=1), sample(2, 2000, epoch=2)])
        first, second, third = self.readings(items)
        self.assertIsNone(first.ident)          # sample precedes any identity
        self.assertEqual(second.ident.sensor_id, 4242)
        self.assertIsNone(third.ident)          # configuration changed after the identity frame


class CsvTests(unittest.TestCase):
    def test_columns_and_blank_identity(self):
        out = io.StringIO()
        log = ock.CsvLog(out)
        items, _ = ock.replay([sample(0, 1000, 5000, 3700, epoch=1),
                               ock.encode_ident(350000, 594, 1000, 4242, 7, epoch=1),
                               sample(1, 2000, -250, ock.TEMP_INVALID, epoch=1)])
        for item in items:
            if isinstance(item, ock.Reading):
                log.write(item, 1700000000.5)
        rows = out.getvalue().splitlines()
        self.assertEqual(rows[0], "device_time_ms,host_time_unix_s,sequence,raw_current_pa,temp_mc,status,"
                                  "strip_lot,calibration_id,lost_before")
        self.assertEqual(rows[1], "1000,1700000000.500,0,5000,37000,0x40,,,0")
        self.assertEqual(rows[2], "2000,1700000000.500,1,-250,,0x42,4242,7,0")


if __name__ == "__main__":
    unittest.main()
