"""Decoder for the Open CGM Kit framed sensor protocol, version 1 (docs/PROTOCOL.md).

Pure Python, no BLE or Resilient dependency. Mirrors firmware/common/ock_frame.h.
"""

from __future__ import annotations

import binascii
import csv
from dataclasses import dataclass
import struct
from typing import Iterable, TextIO

SYNC = 0xA5
VERSION = 1
FRAME_LEN = 20
KIND_SAMPLE = 0x01
KIND_IDENT = 0x02
TEMP_INVALID = -32768

ST_OVERRANGE = 0x01
ST_TEMP_INVALID = 0x02
ST_TEMP_DIE = 0x04
ST_SETTLING = 0x08
ST_DROPPED = 0x10
EPOCH_SHIFT = 6

_MAX_PLAUSIBLE_LEN = 64


class FrameError(ValueError):
    """Base class; `kind` matches the Fault.kind reported by FrameStream."""
    kind = "frame_error"


class TruncatedFrame(FrameError):
    kind = "truncated"


class CrcError(FrameError):
    kind = "crc"


class VersionMismatch(FrameError):
    kind = "version_mismatch"


class BadFrame(FrameError):
    kind = "bad_frame"


class SequenceRegression(FrameError):
    kind = "sequence_regression"


def crc16(data: bytes) -> int:
    """CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF)."""
    return binascii.crc_hqx(data, 0xFFFF)


@dataclass(frozen=True)
class Sample:
    status: int
    seq: int
    t_ms: int
    current_pa: int
    temp_cc: int

    @property
    def epoch(self) -> int:
        return self.status >> EPOCH_SHIFT

    @property
    def temp_valid(self) -> bool:
        return not self.status & ST_TEMP_INVALID and self.temp_cc != TEMP_INVALID

    @property
    def temp_mc(self) -> int | None:
        return self.temp_cc * 10 if self.temp_valid else None


@dataclass(frozen=True)
class Ident:
    status: int
    technique: int
    rtia_ohm: int
    bias_mv: int
    period_ms: int
    sensor_id: int
    cal_id: int

    @property
    def epoch(self) -> int:
        return self.status >> EPOCH_SHIFT


@dataclass(frozen=True)
class Reading:
    """A decoded sample with stream context."""
    sample: Sample
    seq_ext: int            # sequence with 16-bit wraps unwrapped, first sample = its own seq
    device_time_ms: int     # t_ms with 32-bit wraps unwrapped
    lost_before: int        # samples missing between the previous reading and this one
    ident: Ident | None     # identity whose epoch matches the sample, else None


@dataclass(frozen=True)
class Fault:
    kind: str
    detail: str


def _seal(body: bytes) -> bytes:
    return body + struct.pack("<H", crc16(body))


def encode_sample(seq: int, t_ms: int, current_pa: int, temp_cc: int = TEMP_INVALID, status: int = 0,
                  epoch: int = 0) -> bytes:
    if temp_cc == TEMP_INVALID:
        status |= ST_TEMP_INVALID
    status = (status & 0x3F) | (epoch << EPOCH_SHIFT)
    return _seal(struct.pack("<BBBBBBHIih", SYNC, VERSION, FRAME_LEN, KIND_SAMPLE, status, 0, seq & 0xFFFF,
                             t_ms & 0xFFFFFFFF, current_pa, temp_cc))


def encode_ident(rtia_ohm: int, bias_mv: int, period_ms: int, sensor_id: int, cal_id: int,
                 technique: int = 1, epoch: int = 0) -> bytes:
    body = struct.pack("<BBBBBBHhHIH", SYNC, VERSION, FRAME_LEN, KIND_IDENT, epoch << EPOCH_SHIFT,
                       technique, rtia_ohm // 10, bias_mv, period_ms, sensor_id, cal_id)
    return _seal(body)


def decode_frame(data: bytes) -> Sample | Ident:
    """Decode exactly one frame. Raises a FrameError subclass on any defect."""
    if len(data) < 3:
        raise TruncatedFrame(f"{len(data)} bytes, need a 3-byte header")
    if data[0] != SYNC:
        raise BadFrame(f"bad sync byte 0x{data[0]:02x}")
    if data[1] != VERSION:
        raise VersionMismatch(f"frame version {data[1]}, decoder supports {VERSION}")
    if data[2] != FRAME_LEN:
        raise BadFrame(f"frame length field {data[2]}, expected {FRAME_LEN}")
    if len(data) < FRAME_LEN:
        raise TruncatedFrame(f"{len(data)} of {FRAME_LEN} bytes")
    if len(data) > FRAME_LEN:
        raise BadFrame(f"{len(data) - FRAME_LEN} trailing bytes")
    received, = struct.unpack_from("<H", data, FRAME_LEN - 2)
    if received != crc16(data[:FRAME_LEN - 2]):
        raise CrcError("CRC mismatch")
    kind = data[3]
    if kind == KIND_SAMPLE:
        _, _, _, _, status, _, seq, t_ms, current, temp = struct.unpack_from("<BBBBBBHIih", data)
        return Sample(status, seq, t_ms, current, temp)
    if kind == KIND_IDENT:
        _, _, _, _, status, technique, rtia, bias, period, sensor, cal = struct.unpack_from("<BBBBBBHhHIH", data)
        return Ident(status, technique, rtia * 10, bias, period, sensor, cal)
    raise BadFrame(f"unknown frame kind 0x{kind:02x}")


class FrameStream:
    """Reassemble frames from notification chunks of any size.

    feed() returns Reading, Ident and Fault items in arrival order. With strict=True the
    first fault raises the matching FrameError instead. Byte loss is recovered by scanning
    for the next sync byte whose frame passes its CRC.
    """

    def __init__(self, strict: bool = False) -> None:
        self.strict = strict
        self.pending = bytearray()
        self.ident: Ident | None = None
        self.stats = {"frames": 0, "crc_failures": 0, "version_mismatches": 0, "bad_frames": 0,
                      "resync_bytes": 0, "lost_samples": 0, "regressions": 0, "truncated": 0}
        self._last_seq: int | None = None
        self._seq_ext = 0
        self._last_t: int | None = None
        self._t_ext = 0

    def _fault(self, error: FrameError) -> Fault:
        if self.strict:
            raise error
        return Fault(error.kind, str(error))

    def feed(self, chunk: bytes) -> list:
        if len(chunk) > 512:
            raise ValueError("notification exceeds supported ATT payload size")
        self.pending.extend(chunk)
        items: list = []
        buf = self.pending
        while buf:
            index = buf.find(SYNC)
            if index < 0:
                self.stats["resync_bytes"] += len(buf)
                buf.clear()
                break
            if index:
                self.stats["resync_bytes"] += index
                del buf[:index]
            if len(buf) < 3:
                break
            if buf[1] != VERSION or buf[2] != FRAME_LEN:
                if buf[1] != VERSION and 4 <= buf[2] <= _MAX_PLAUSIBLE_LEN:
                    self.stats["version_mismatches"] += 1
                    items.append(self._fault(VersionMismatch(
                        f"frame version {buf[1]}, decoder supports {VERSION}")))
                else:
                    self.stats["resync_bytes"] += 1
                del buf[:1]
                continue
            if len(buf) < FRAME_LEN:
                break
            try:
                decoded = decode_frame(bytes(buf[:FRAME_LEN]))
            except CrcError as error:
                self.stats["crc_failures"] += 1
                items.append(self._fault(error))
                del buf[:1]
                continue
            except FrameError as error:
                self.stats["bad_frames"] += 1
                items.append(self._fault(error))
                del buf[:1]
                continue
            del buf[:FRAME_LEN]
            self.stats["frames"] += 1
            items.extend(self._accept(decoded))
        return items

    def _accept(self, decoded: Sample | Ident) -> list:
        if isinstance(decoded, Ident):
            self.ident = decoded
            return [decoded]
        lost = 0
        if self._last_seq is not None:
            delta = (decoded.seq - self._last_seq - 1) & 0xFFFF
            tdelta = (decoded.t_ms - self._last_t) & 0xFFFFFFFF
            if delta >= 0x8000 or tdelta >= 0x80000000:
                self.stats["regressions"] += 1
                return [self._fault(SequenceRegression(
                    f"sequence {decoded.seq} after {self._last_seq}, device time step {tdelta} ms"))]
            lost = delta
            self._seq_ext += lost + 1
            self._t_ext += tdelta
        else:
            self._seq_ext = decoded.seq
            self._t_ext = decoded.t_ms
        self._last_seq = decoded.seq
        self._last_t = decoded.t_ms
        self.stats["lost_samples"] += lost
        ident = self.ident if self.ident is not None and self.ident.epoch == decoded.epoch else None
        return [Reading(decoded, self._seq_ext, self._t_ext, lost, ident)]

    def finish(self) -> list[Fault]:
        """Report bytes left over at end of capture as a truncated frame."""
        if not self.pending:
            return []
        count = len(self.pending)
        self.pending.clear()
        self.stats["truncated"] += 1
        return [self._fault(TruncatedFrame(f"{count} trailing bytes do not form a frame"))]


CSV_COLUMNS = ("device_time_ms", "host_time_unix_s", "sequence", "raw_current_pa", "temp_mc",
               "status", "strip_lot", "calibration_id", "lost_before")


class CsvLog:
    """One row per sample. Strip lot and calibration id are blank until a matching identity frame arrives."""

    def __init__(self, stream: TextIO) -> None:
        self.writer = csv.writer(stream, lineterminator="\n")
        self.writer.writerow(CSV_COLUMNS)
        self.stream = stream

    def write(self, reading: Reading, host_time_s: float) -> None:
        sample, ident = reading.sample, reading.ident
        self.writer.writerow((
            reading.device_time_ms, f"{host_time_s:.3f}", reading.seq_ext, sample.current_pa,
            "" if sample.temp_mc is None else sample.temp_mc, f"0x{sample.status:02x}",
            "" if ident is None else ident.sensor_id, "" if ident is None else ident.cal_id,
            reading.lost_before))
        self.stream.flush()


def replay(chunks: Iterable[bytes], strict: bool = False) -> tuple[list, FrameStream]:
    """Feed recorded notifications through a fresh stream; returns all items and the stream."""
    stream = FrameStream(strict=strict)
    items: list = []
    for chunk in chunks:
        items.extend(stream.feed(chunk))
    items.extend(stream.finish())
    return items, stream
