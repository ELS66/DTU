"""Reference encoder/decoder for the telemetry v1 wire format."""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass

MAGIC = b"DT"
VERSION = 1
TYPE_TELEMETRY = 1
MAX_FRAME = 4096
HEADER = struct.Struct(">2sBBII16sQqBH")
POINT = struct.Struct(">HBBiH")
FORMATS = {1: ">H", 2: ">h", 3: ">I", 4: ">i", 5: ">f", 6: ">B"}


@dataclass(frozen=True)
class Reading:
    point_code: int
    raw_type: int
    quality: int
    sample_offset_ms: int
    value: int | float | bool | None


@dataclass(frozen=True)
class Telemetry:
    config_revision: int
    boot_id: bytes
    sequence: int
    sample_time_ms: int
    replayed: bool
    time_trusted: bool
    points: tuple[Reading, ...]


def _validate_common(message: Telemetry) -> None:
    if message.config_revision < 1 or message.config_revision > 0xFFFFFFFF:
        raise ValueError("invalid config revision")
    if len(message.boot_id) != 16:
        raise ValueError("boot ID must be 16 bytes")
    if not 1 <= message.sequence <= 0x7FFFFFFFFFFFFFFF:
        raise ValueError("invalid sequence")
    if not 1 <= len(message.points) <= 128:
        raise ValueError("invalid point count")
    if message.sample_time_ms < 0 or message.time_trusted != (message.sample_time_ms > 0):
        raise ValueError("time flag and timestamp disagree")
    if not message.time_trusted and any(p.sample_offset_ms for p in message.points):
        raise ValueError("untrusted time cannot have point offsets")
    if len({p.point_code for p in message.points}) != len(message.points):
        raise ValueError("duplicate point code")


def _encode_point(point: Reading) -> bytes:
    if not 1 <= point.point_code <= 0xFFFF or point.raw_type not in FORMATS:
        raise ValueError("invalid point code or raw type")
    if point.quality not in range(4):
        raise ValueError("invalid quality")
    if point.quality:
        if point.value is not None:
            raise ValueError("bad-quality point must omit value")
        raw = b""
    else:
        if point.value is None:
            raise ValueError("good point requires value")
        if point.raw_type == 6 and point.value not in (0, 1, False, True):
            raise ValueError("invalid boolean")
        if point.raw_type == 5 and not math.isfinite(float(point.value)):
            raise ValueError("non-finite float")
        raw = struct.pack(FORMATS[point.raw_type], point.value)
    return POINT.pack(point.point_code, point.raw_type, point.quality,
                      point.sample_offset_ms, len(raw)) + raw


def encode(message: Telemetry) -> bytes:
    _validate_common(message)
    payload = b"".join(_encode_point(point) for point in message.points)
    flags = int(message.replayed) | (int(message.time_trusted) << 1)
    result = HEADER.pack(MAGIC, VERSION, TYPE_TELEMETRY, len(payload),
                         message.config_revision, message.boot_id,
                         message.sequence, message.sample_time_ms,
                         flags, len(message.points)) + payload
    if len(result) > MAX_FRAME:
        raise ValueError("frame too large")
    return result


def decode(frame: bytes) -> Telemetry:
    if len(frame) < HEADER.size or len(frame) > MAX_FRAME:
        raise ValueError("invalid frame length")
    magic, version, kind, length, revision, boot_id, sequence, sample_time, flags, count = HEADER.unpack_from(frame)
    if magic != MAGIC or version != VERSION or kind != TYPE_TELEMETRY or flags & ~3:
        raise ValueError("invalid header")
    if HEADER.size + length != len(frame):
        raise ValueError("payload length mismatch")
    cursor = HEADER.size
    readings: list[Reading] = []
    for _ in range(count):
        if cursor + POINT.size > len(frame):
            raise ValueError("truncated point")
        code, raw_type, quality, offset, value_len = POINT.unpack_from(frame, cursor)
        cursor += POINT.size
        if raw_type not in FORMATS or quality not in range(4) or cursor + value_len > len(frame):
            raise ValueError("invalid point")
        expected_len = 0 if quality else struct.calcsize(FORMATS[raw_type])
        if value_len != expected_len:
            raise ValueError("invalid value length")
        raw = frame[cursor:cursor + value_len]
        cursor += value_len
        value = None if quality else struct.unpack(FORMATS[raw_type], raw)[0]
        if raw_type == 6 and value is not None:
            if value not in (0, 1):
                raise ValueError("invalid boolean")
            value = bool(value)
        if raw_type == 5 and value is not None and not math.isfinite(value):
            raise ValueError("non-finite float")
        readings.append(Reading(code, raw_type, quality, offset, value))
    if cursor != len(frame):
        raise ValueError("unexpected trailing data")
    message = Telemetry(revision, boot_id, sequence, sample_time,
                        bool(flags & 1), bool(flags & 2), tuple(readings))
    _validate_common(message)
    return message
