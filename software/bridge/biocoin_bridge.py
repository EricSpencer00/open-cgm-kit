#!/usr/bin/env python3
"""Bench-only Biocoin CA receiver and Resilient domain-core adapter."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time

from ock_protocol import CsvLog, FrameStream, Fault, Ident, Reading, ST_OVERRANGE, ST_SETTLING

SERVICE_UUID = "00001523-1212-efde-1523-785feabc93aa"
CONFIG_UUID = "0000152a-1212-efde-1523-785feabc93aa"
CONTROL_UUID = "00001528-1212-efde-1523-785feabc93aa"
DATA_UUID = "00001529-1212-efde-1523-785feabc93aa"
STATUS_UUID = "00001524-1212-efde-1523-785feabc93aa"
CORE_PATH = Path(__file__).resolve().parents[1] / "resilient" / "glucose_core.rz"
CAL_FIELDS = (
    "enabled", "id", "low_current_pa", "high_current_pa", "low_glucose_mgdl",
    "high_glucose_mgdl", "min_temp_mc", "max_temp_mc",
)
SAMPLE_FIELDS = ("sequence", "raw_current_pa", "temp_mc", "age_ms", "sensor_state")
# Allowed patched-Biocoin RTIA values in kOhm (AD5940 LPTIARTIA_10K..512K), matching the firmware table.
BIOCOIN_RTIA_KOHM = (10, 12, 16, 20, 24, 30, 32, 40, 48, 64, 85, 96, 100, 120, 128, 160, 196, 256, 512)
DEFAULT_BIOCOIN_RTIA_KOHM = 512


class CurrentStream:
    """Reassemble upstream's little-endian float32 microampere stream."""

    def __init__(self) -> None:
        self.pending = bytearray()

    def feed(self, payload: bytes) -> list[int]:
        if len(payload) > 512:
            raise ValueError("notification exceeds supported ATT payload size")
        self.pending.extend(payload)
        result = []
        while len(self.pending) >= 4:
            value_ua = struct.unpack("<f", self.pending[:4])[0]
            del self.pending[:4]
            if not math.isfinite(value_ua):
                raise ValueError("non-finite electrode current")
            current_pa = round(value_ua * 1_000_000)
            if abs(current_pa) > 1_000_000_000:
                raise ValueError("electrode current exceeds core bounds")
            result.append(current_pa)
        return result

    def finish(self) -> None:
        if self.pending:
            raise ValueError("truncated float32 stream")


def parse_status(payload: bytes) -> int:
    if len(payload) != 1 or payload[0] not in range(5):
        raise ValueError("invalid Biocoin status payload")
    return payload[0]


def ca_payload(sampling_s: float, processing_s: float, max_current_ua: float,
               bias_mv: float, channel: int, rtia_kohm: int | None = None,
               sensor_id: int = 0, cal_id: int = 0) -> bytes:
    # The upstream SDK names this field uA; firmware calls it an mA hint.
    # Pinned CA firmware never applies it to the fixed 10k RTIA or current limit.
    values = (sampling_s, processing_s, max_current_ua, bias_mv)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("CA parameters must be finite")
    if not 0 < sampling_s <= processing_s <= 3600:
        raise ValueError("require 0 < sampling <= processing <= 3600 seconds")
    if not 0 < max_current_ua <= 1000:
        raise ValueError("maximum current must fit this core's 1000 uA bound")
    if not -1000 <= bias_mv <= 1000 or channel not in range(4):
        raise ValueError("bias must be within +/-1000 mV and channel within 0..3")
    base = struct.pack("<BffffB", 1, sampling_s, processing_s, max_current_ua, bias_mv, channel)
    if rtia_kohm is None:
        return base
    # Patched firmware (firmware/biocoin-patches): 25-byte parameters, 26 with the technique byte.
    if rtia_kohm not in BIOCOIN_RTIA_KOHM:
        raise ValueError("RTIA must be one of " + ", ".join(map(str, BIOCOIN_RTIA_KOHM)) + " kOhm")
    if not 0 <= sensor_id < 2**32 or not 0 <= cal_id < 2**16:
        raise ValueError("sensor id must fit 32 bits and calibration id 16 bits")
    return base + struct.pack("<HIH", rtia_kohm, sensor_id, cal_id)


def strip_rig_payload(tia_gain_code: int, bias_mv: int, period_ms: int,
                      sensor_id: int = 0, cal_id: int = 0) -> bytes:
    """Strip rig CONFIG characteristic: <BBhHIH, version 1. TIA gain codes 1..7 are 2.75k..350k."""
    if tia_gain_code not in range(1, 8):
        raise ValueError("TIA gain code must be 1..7")
    if not -32768 <= bias_mv <= 32767 or not 100 <= period_ms <= 60000:
        raise ValueError("bias must fit int16 and period be 100..60000 ms")
    if not 0 <= sensor_id < 2**32 or not 0 <= cal_id < 2**16:
        raise ValueError("sensor id must fit 32 bits and calibration id 16 bits")
    return struct.pack("<BBhHIH", 1, tia_gain_code, bias_mv, period_ms, sensor_id, cal_id)


def synthetic_calibration() -> dict:
    return dict(zip(CAL_FIELDS, (True, 1, -200, 3400, 40, 400, 35000, 39000)))


def rz_struct(name: str, fields: tuple[str, ...], values: dict) -> str:
    if set(values) != set(fields):
        raise ValueError(f"unexpected {name} fields")
    encoded = []
    for field in fields:
        value = values[field]
        if field == "enabled":
            if type(value) is not bool:
                raise ValueError("enabled must be a boolean")
            literal = "true" if value else "false"
        else:
            if type(value) is not int or not -(2**63) <= value < 2**63:
                raise ValueError(f"{field} must be a signed int64")
            literal = str(value)
        encoded.append(f"{field}: {literal}")
    return "new " + name + " { " + ", ".join(encoded) + " }"


def run_core(sample: dict, calibration: dict, rz_binary: str, max_age_ms: int = 300000) -> dict:
    if type(max_age_ms) is not int or not 1 <= max_age_ms <= 3600000:
        raise ValueError("invalid max age")
    source = "use " + json.dumps(str(CORE_PATH)) + ";\n"
    source += "let sample = " + rz_struct("SensorSample", SAMPLE_FIELDS, sample) + ";\n"
    source += "let cal = " + rz_struct("Calibration", CAL_FIELDS, calibration) + ";\n"
    source += f"let evaluated = evaluate(sample, cal, {max_age_ms});\n"
    source += 'println("CGM_RESULT|" + evaluated.status + "|" + evaluated.has_glucose + "|" + evaluated.glucose_mgdl + "|" + evaluated.calibration_id);\n'
    with tempfile.TemporaryDirectory(prefix="open-cgm-rz-") as directory:
        path = Path(directory) / "evaluation.rz"
        path.write_text(source, encoding="utf-8")
        result = subprocess.run(
            [rz_binary, "--seed", "1", "--panic-on-fault", str(path)],
            text=True, capture_output=True, timeout=5, check=False,
        )
    if result.returncode:
        raise RuntimeError("Resilient evaluation failed: " + result.stderr[-1000:])
    lines = [line for line in result.stdout.splitlines() if line.startswith("CGM_RESULT|")]
    if len(lines) != 1:
        raise RuntimeError("missing or ambiguous Resilient result")
    _, status, available, glucose, cal_id = lines[0].split("|")
    if available not in {"true", "false"}:
        raise RuntimeError("invalid availability from core")
    return {
        "status": status,
        "glucose_mgdl": int(glucose) if available == "true" else None,
        "calibration_id": int(cal_id) if available == "true" else None,
    }


def load_calibration(path: str) -> dict:
    """Lab-issued calibration JSON: the Resilient fields, plus optional "strip_lot" to pin a strip lot."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    extra = set(data) - set(CAL_FIELDS) - {"strip_lot"}
    if not isinstance(data, dict) or extra or not set(CAL_FIELDS) <= set(data):
        raise ValueError("calibration file must hold exactly the fields " + ", ".join(CAL_FIELDS)
                         + " and optionally strip_lot")
    return data


def evaluate_reading(reading: Reading, calibration: dict | None, rz_binary: str) -> dict:
    """Run one framed sample through the Resilient core.

    The calibration is offered to the core only when the device's current identity frame names
    the same calibration id (and strip lot, if the file pins one). Otherwise the core sees a
    disabled calibration and no glucose can be produced.
    """
    sample, ident = reading.sample, reading.ident
    usable = (calibration is not None and ident is not None and ident.cal_id == calibration["id"]
              and calibration.get("strip_lot") in (None, ident.sensor_id))
    if usable:
        cal = {field: calibration[field] for field in CAL_FIELDS}
    else:
        cal = synthetic_calibration()
        cal["enabled"] = False
        cal["id"] = 0
    if sample.status & ST_OVERRANGE:
        state = 3
    elif sample.status & ST_SETTLING:
        state = 1
    else:
        state = 2
    temp_mc = sample.temp_mc if sample.temp_mc is not None else -40001
    # Age is receipt age: device time is not synchronized to the host, so it is 0 at receipt.
    core_sample = dict(zip(SAMPLE_FIELDS, (reading.seq_ext, sample.current_pa, temp_mc, 0, state)))
    result = run_core(core_sample, cal, rz_binary)
    if not usable:
        result["glucose_mgdl"] = None
        result["calibration_id"] = None
    return result


class FramedSink:
    """Turn decoded protocol items into JSON records, CSV rows and Resilient results."""

    def __init__(self, rz_binary: str, calibration: dict | None = None, csv_log: CsvLog | None = None) -> None:
        self.rz_binary = rz_binary
        self.calibration = calibration
        self.csv_log = csv_log

    def handle(self, item, host_time_s: float) -> None:
        if isinstance(item, Reading):
            if self.csv_log is not None:
                self.csv_log.write(item, host_time_s)
            result = evaluate_reading(item, self.calibration, self.rz_binary)
            sample, ident = item.sample, item.ident
            emit({"source": "ock_frame", "device_sequence": item.seq_ext,
                  "device_time_ms": item.device_time_ms, "host_time_unix_s": round(host_time_s, 3),
                  "raw_current_pA": sample.current_pa, "temp_mC": sample.temp_mc,
                  "status_flags": sample.status & 0x3F, "lost_before": item.lost_before,
                  "strip_lot": None if ident is None else ident.sensor_id,
                  "device_calibration_id": None if ident is None else ident.cal_id, **result})
        elif isinstance(item, Ident):
            emit({"source": "ock_frame", "status": "identity", "technique": item.technique,
                  "rtia_ohm": item.rtia_ohm, "bias_mV": item.bias_mv, "period_ms": item.period_ms,
                  "strip_lot": item.sensor_id, "device_calibration_id": item.cal_id,
                  "epoch": item.epoch, "glucose_mgdl": None})
        elif isinstance(item, Fault):
            emit({"source": "ock_frame", "status": "frame_fault", "kind": item.kind,
                  "detail": item.detail, "glucose_mgdl": None})


def read_capture(path: str) -> list[bytes]:
    """Recorded notifications: a .hex file (one notification per line, # comments) or raw bytes."""
    if path.endswith(".hex"):
        lines = Path(path).read_text(encoding="ascii").splitlines()
        return [bytes.fromhex(line.split("#")[0].strip()) for line in lines if line.split("#")[0].strip()]
    return [Path(path).read_bytes()]


def replay_capture(path: str, sink: FramedSink) -> FrameStream:
    stream = FrameStream()
    host_time = time.time()
    for chunk in read_capture(path):
        for item in stream.feed(chunk):
            sink.handle(item, host_time)
    for item in stream.finish():
        sink.handle(item, host_time)
    emit({"source": "ock_frame", "status": "replay_ended", "glucose_mgdl": None, **stream.stats})
    return stream


def emit(record: dict) -> None:
    print(json.dumps(record, allow_nan=False, separators=(",", ":")), flush=True)


def demo(rz_binary: str) -> None:
    current = CurrentStream().feed(struct.pack("<f", 0.0016))[0]
    sample = dict(zip(SAMPLE_FIELDS, (1, current, 37000, 0, 2)))
    result = run_core(sample, synthetic_calibration(), rz_binary)
    emit({"source": "synthetic_fixture", "measured_on_hardware": False,
          "raw_current_pA": current, "temp_mC": 37000, **result})


async def receive(args: argparse.Namespace) -> None:
    try:
        from bleak import BleakClient
    except ImportError as error:
        raise RuntimeError("BLE mode requires bleak; see software/bridge/README.md") from error

    payload = ca_payload(args.sampling_s, args.processing_s, args.max_current_ua,
                         args.bias_mv, args.channel)
    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    failure = asyncio.Event()
    stream = CurrentStream()
    sequence = 0
    calibration = synthetic_calibration()
    calibration["enabled"] = False
    calibration["id"] = 0

    async def publish_sample(item: tuple[int, int, int]) -> None:
        seq, received_ms, current = item
        host_age = time.monotonic_ns() // 1_000_000 - received_ms
        # CA has no temperature or acquisition timestamps. Invalid sentinels
        # keep those missing observations from becoming glucose estimates.
        sample = dict(zip(SAMPLE_FIELDS, (seq, current, -40001, -1, 1)))
        result = await asyncio.to_thread(run_core, sample, calibration, args.rz_bin)
        emit({"source": "biocoin_ble", "host_sequence": seq,
              "raw_current_pA": current, "temp_mC": None,
              "acquisition_age_ms": None, "host_receipt_age_ms": host_age,
              "device_sequence_available": False,
              "unavailable_reasons": ["no_temperature", "no_acquisition_timestamp", "uncalibrated"],
              **result})

    async def drain_tail() -> None:
        # STOP flushes firmware FIFO/TX asynchronously. A quiet window is useful
        # for bench logs but cannot prove completion without a device end marker.
        deadline = time.monotonic() + 2
        while not failure.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            try:
                item = await asyncio.wait_for(queue.get(), timeout=min(0.25, remaining))
            except asyncio.TimeoutError:
                return
            await publish_sample(item)

    def notification(_sender, data: bytearray) -> None:
        nonlocal sequence
        try:
            received_ms = time.monotonic_ns() // 1_000_000
            for current in stream.feed(bytes(data)):
                sequence += 1
                queue.put_nowait((sequence, received_ms, current))
        except (ValueError, asyncio.QueueFull) as error:
            emit({"source": "biocoin_ble", "status": "transport_fault",
                  "error": str(error), "glucose_mgdl": None})
            failure.set()

    async with BleakClient(args.address, disconnected_callback=lambda _c: failure.set()) as client:
        if not any(service.uuid.lower() == SERVICE_UUID for service in client.services):
            raise RuntimeError("device does not expose the Biocoin service")
        initial_status = parse_status(bytes(await client.read_gatt_char(STATUS_UUID)))
        if initial_status != 0:
            raise RuntimeError(f"device is not idle, status={initial_status}; existing run left untouched")
        await client.start_notify(DATA_UUID, notification)
        start_attempted = False
        primary_error = None
        try:
            await client.write_gatt_char(CONFIG_UUID, payload, response=True)
            await asyncio.sleep(1)
            status = parse_status(bytes(await client.read_gatt_char(STATUS_UUID)))
            if status != 0:
                raise RuntimeError(f"device rejected CA configuration, status={status}")
            # Mark ownership before the write: its acknowledgement could fail
            # even after firmware received START, requiring best-effort STOP.
            start_attempted = True
            await client.write_gatt_char(CONTROL_UUID, b"\x01", response=True)
            start_deadline = time.monotonic() + 2
            while True:
                status = parse_status(bytes(await client.read_gatt_char(STATUS_UUID)))
                if status == 2:
                    break
                if status in {1, 3, 4} or time.monotonic() >= start_deadline:
                    raise RuntimeError(f"CA acquisition failed to start, status={status}")
                await asyncio.sleep(0.1)
            deadline = time.monotonic() + args.duration_s
            while time.monotonic() < deadline and not failure.is_set():
                status = parse_status(bytes(await client.read_gatt_char(STATUS_UUID)))
                if status != 2:
                    raise RuntimeError(f"CA acquisition not running, status={status}")
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=1)
                except asyncio.TimeoutError:
                    emit({"source": "biocoin_ble", "status": "no_recent_data", "glucose_mgdl": None})
                    continue
                await publish_sample(item)
            if failure.is_set():
                raise RuntimeError("BLE disconnected or stream failed; cached glucose must be cleared")
        except BaseException as error:
            primary_error = error
            raise
        finally:
            cleanup_error = None
            if client.is_connected:
                try:
                    if start_attempted:
                        await client.write_gatt_char(CONTROL_UUID, b"\xff", response=True)
                        status = parse_status(bytes(await client.read_gatt_char(STATUS_UUID)))
                        if status != 0:
                            raise RuntimeError(f"device did not confirm STOP, status={status}")
                        await drain_tail()
                        if failure.is_set():
                            raise RuntimeError("transport failed while draining STOP tail")
                except Exception as error:
                    cleanup_error = error
                finally:
                    try:
                        await client.stop_notify(DATA_UUID)
                    except Exception as error:
                        if cleanup_error is None:
                            cleanup_error = error
            elif start_attempted:
                cleanup_error = RuntimeError("disconnected before STOP could be confirmed")
            try:
                stream.finish()
            except ValueError as error:
                if cleanup_error is None:
                    cleanup_error = error
            emit({"source": "biocoin_ble", "status": "capture_ended",
                  "capture_complete": False, "glucose_mgdl": None,
                  "completion_limit": "upstream_has_no_end_marker_or_device_sequence"})
            if cleanup_error is not None:
                if primary_error is not None:
                    emit({"source": "biocoin_ble", "status": "cleanup_fault",
                          "error": str(cleanup_error), "glucose_mgdl": None})
                else:
                    raise RuntimeError("capture cleanup failed: " + str(cleanup_error)) from cleanup_error
    emit({"source": "biocoin_ble", "status": "disconnected", "glucose_mgdl": None})


async def receive_framed(args: argparse.Namespace, config: bytes, sink: FramedSink) -> None:
    """Capture OCK frames from the strip rig or patched Biocoin (same GATT layout)."""
    try:
        from bleak import BleakClient
    except ImportError as error:
        raise RuntimeError("BLE mode requires bleak; see software/bridge/README.md") from error

    queue: asyncio.Queue = asyncio.Queue(maxsize=1024)
    failure = asyncio.Event()
    stream = FrameStream()

    def notification(_sender, data: bytearray) -> None:
        received = time.time()
        try:
            for item in stream.feed(bytes(data)):
                queue.put_nowait((received, item))
        except (ValueError, asyncio.QueueFull) as error:
            emit({"source": "ock_frame", "status": "transport_fault", "error": str(error),
                  "glucose_mgdl": None})
            failure.set()

    async def drain(until: float) -> None:
        while not failure.is_set():
            remaining = until - time.monotonic()
            if remaining <= 0:
                return
            try:
                received, item = await asyncio.wait_for(queue.get(), timeout=min(0.25, remaining))
            except asyncio.TimeoutError:
                return
            await asyncio.to_thread(sink.handle, item, received)

    async with BleakClient(args.address, disconnected_callback=lambda _c: failure.set()) as client:
        if not any(service.uuid.lower() == SERVICE_UUID for service in client.services):
            raise RuntimeError("device does not expose the expected service")
        initial_status = parse_status(bytes(await client.read_gatt_char(STATUS_UUID)))
        if initial_status != 0:
            raise RuntimeError(f"device is not idle, status={initial_status}; existing run left untouched")
        await client.start_notify(DATA_UUID, notification)
        start_attempted = False
        primary_error = None
        try:
            await client.write_gatt_char(CONFIG_UUID, config, response=True)
            await asyncio.sleep(0.5)
            status = parse_status(bytes(await client.read_gatt_char(STATUS_UUID)))
            if status != 0:
                raise RuntimeError(f"device rejected configuration, status={status}")
            start_attempted = True
            await client.write_gatt_char(CONTROL_UUID, b"\x01", response=True)
            start_deadline = time.monotonic() + 3
            while True:
                status = parse_status(bytes(await client.read_gatt_char(STATUS_UUID)))
                if status == 2:
                    break
                if status in {1, 3, 4} or time.monotonic() >= start_deadline:
                    raise RuntimeError(f"acquisition failed to start, status={status}")
                await asyncio.sleep(0.1)
            deadline = time.monotonic() + args.duration_s
            while time.monotonic() < deadline and not failure.is_set():
                try:
                    received, item = await asyncio.wait_for(queue.get(), timeout=1)
                except asyncio.TimeoutError:
                    emit({"source": "ock_frame", "status": "no_recent_data", "glucose_mgdl": None})
                    continue
                await asyncio.to_thread(sink.handle, item, received)
            if failure.is_set():
                raise RuntimeError("BLE disconnected or stream failed; cached glucose must be cleared")
        except BaseException as error:
            primary_error = error
            raise
        finally:
            cleanup_error = None
            if client.is_connected:
                try:
                    if start_attempted:
                        await client.write_gatt_char(CONTROL_UUID, b"\xff", response=True)
                        status = parse_status(bytes(await client.read_gatt_char(STATUS_UUID)))
                        if status != 0:
                            raise RuntimeError(f"device did not confirm STOP, status={status}")
                        await drain(time.monotonic() + 1)
                except Exception as error:
                    cleanup_error = error
                finally:
                    try:
                        await client.stop_notify(DATA_UUID)
                    except Exception as error:
                        if cleanup_error is None:
                            cleanup_error = error
            elif start_attempted:
                # The strip rig stops itself on disconnect; upstream Biocoin does not. Either way,
                # confirm a stopped status when reconnecting.
                cleanup_error = RuntimeError("disconnected before STOP could be confirmed")
            for item in stream.finish():
                sink.handle(item, time.time())
            emit({"source": "ock_frame", "status": "capture_ended", "glucose_mgdl": None, **stream.stats})
            if cleanup_error is not None:
                if primary_error is not None:
                    emit({"source": "ock_frame", "status": "cleanup_fault", "error": str(cleanup_error),
                          "glucose_mgdl": None})
                else:
                    raise RuntimeError("capture cleanup failed: " + str(cleanup_error)) from cleanup_error
    emit({"source": "ock_frame", "status": "disconnected", "glucose_mgdl": None})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="synthetic bytes, no BLE access")
    parser.add_argument("--rz-bin", default=os.environ.get("RZ_BIN", "rz"))
    parser.add_argument("--address", help="explicit Biocoin BLE address/OS device UUID")
    parser.add_argument("--sampling-s", type=float)
    parser.add_argument("--processing-s", type=float)
    parser.add_argument("--max-current-ua", type=float)
    parser.add_argument("--bias-mv", type=float)
    parser.add_argument("--channel", type=int)
    parser.add_argument("--duration-s", type=float, default=30)
    parser.add_argument("--device", choices=("biocoin", "biocoin-ock", "strip-rig"), default="biocoin",
                        help="biocoin: pinned upstream float stream; biocoin-ock: patched firmware; strip-rig")
    parser.add_argument("--replay", help="replay a recorded .hex/.bin capture of OCK frames, no BLE")
    parser.add_argument("--csv", help="write the per-sample CSV log here (OCK frames)")
    parser.add_argument("--calibration", help="lab calibration JSON; glucose is never emitted without it")
    parser.add_argument("--rtia-kohm", type=int, default=DEFAULT_BIOCOIN_RTIA_KOHM)
    parser.add_argument("--tia-gain-code", type=int, help="strip rig LMP91000 TIA_GAIN code 1..7")
    parser.add_argument("--period-ms", type=int, help="strip rig sample period")
    parser.add_argument("--sensor-id", type=int, default=0, help="strip lot / serial reported by the device")
    parser.add_argument("--cal-id", type=int, default=0, help="calibration id reported by the device")
    args = parser.parse_args()
    try:
        if args.replay or args.device != "biocoin":
            csv_handle = open(args.csv, "w", newline="", encoding="utf-8") if args.csv else None
            try:
                calibration = load_calibration(args.calibration) if args.calibration else None
                sink = FramedSink(args.rz_bin, calibration, CsvLog(csv_handle) if csv_handle else None)
                if args.replay:
                    replay_capture(args.replay, sink)
                else:
                    if not args.address or args.bias_mv is None:
                        parser.error("BLE mode requires --address and --bias-mv")
                    if not math.isfinite(args.duration_s) or not 0 < args.duration_s <= 3600:
                        parser.error("--duration-s must be finite and within 0..3600")
                    if args.device == "strip-rig":
                        if args.tia_gain_code is None or args.period_ms is None:
                            parser.error("strip-rig requires --tia-gain-code and --period-ms")
                        config = strip_rig_payload(args.tia_gain_code, round(args.bias_mv), args.period_ms,
                                                   args.sensor_id, args.cal_id)
                    else:
                        if any(getattr(args, name) is None for name in
                               ("sampling_s", "processing_s", "max_current_ua", "channel")):
                            parser.error("biocoin-ock requires --sampling-s --processing-s --max-current-ua --channel")
                        config = ca_payload(args.sampling_s, args.processing_s, args.max_current_ua,
                                            args.bias_mv, args.channel, args.rtia_kohm,
                                            args.sensor_id, args.cal_id)
                    asyncio.run(receive_framed(args, config, sink))
            finally:
                if csv_handle:
                    csv_handle.close()
        elif args.demo:
            demo(args.rz_bin)
        else:
            if not args.address or any(getattr(args, name) is None for name in
                                       ("sampling_s", "processing_s", "max_current_ua", "bias_mv", "channel")):
                parser.error("BLE mode requires --address and all five CA parameters")
            if not math.isfinite(args.duration_s) or not 0 < args.duration_s <= 3600:
                parser.error("--duration-s must be finite and within 0..3600")
            asyncio.run(receive(args))
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        emit({"status": "bridge_fault", "glucose_mgdl": None, "error": str(error)})
        return 1
    except KeyboardInterrupt:
        emit({"status": "stopped", "glucose_mgdl": None})
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
