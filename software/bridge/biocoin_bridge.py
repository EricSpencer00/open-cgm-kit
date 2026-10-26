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
               bias_mv: float, channel: int) -> bytes:
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
    return struct.pack("<BffffB", 1, sampling_s, processing_s, max_current_ua, bias_mv, channel)


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
    args = parser.parse_args()
    try:
        if args.demo:
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
